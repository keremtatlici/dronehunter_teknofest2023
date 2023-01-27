from types import SimpleNamespace
from enum import Enum
import logging
import numpy as np
import numba as nb
import cv2

from .detector import SSDDetector, YOLODetector, PublicDetector
from .feature_extractor import FeatureExtractor
from .tracker import MultiTracker
from .utils import Profiler
from .utils.visualization import Visualizer
from .utils.numba import bisect_right


LOGGER = logging.getLogger(__name__)


class DetectorType(Enum):
    SSD = 0
    YOLO = 1
    PUBLIC = 2


class MOT:
    def __init__(self, size,
                 detector_type='YOLO',
                 detector_frame_skip=5,
                 class_ids=(1,),
                 ssd_detector_cfg=None,
                 yolo_detector_cfg=None,
                 public_detector_cfg=None,
                 feature_extractor_cfgs=None,
                 tracker_cfg=None,
                 visualizer_cfg=None,
                 draw=False):
        """Top level module that integrates detection, feature extraction,
        and tracking together.

        Parameters
        ----------
        size : tuple
            Width and height of each frame.
        detector_type : {'SSD', 'YOLO', 'public'}, optional
            Type of detector to use.
        detector_frame_skip : int, optional
            Number of frames to skip for the detector.
        class_ids : sequence, optional
            Class IDs to track. Note class ID starts at zero.
        ssd_detector_cfg : SimpleNamespace, optional
            SSD detector configuration.
        yolo_detector_cfg : SimpleNamespace, optional
            YOLO detector configuration.
        public_detector_cfg : SimpleNamespace, optional
            Public detector configuration.
        feature_extractor_cfgs : List[SimpleNamespace], optional
            Feature extractor configurations for all classes.
            Each configuration corresponds to the class at the same index in sorted `class_ids`.
        tracker_cfg : SimpleNamespace, optional
            Tracker configuration.
        visualizer_cfg : SimpleNamespace, optional
            Visualization configuration.
        draw : bool, optional
            Draw visualizations.
        """
        self.size = size
        self.detector_type = DetectorType[detector_type.upper()]
        assert detector_frame_skip >= 1
        self.detector_frame_skip = detector_frame_skip
        self.class_ids = tuple(np.unique(class_ids))
        self.draw = draw

        if ssd_detector_cfg is None:
            ssd_detector_cfg = SimpleNamespace()
        if yolo_detector_cfg is None:
            yolo_detector_cfg = SimpleNamespace()
        if public_detector_cfg is None:
            public_detector_cfg = SimpleNamespace()
        if feature_extractor_cfgs is None:
            feature_extractor_cfgs = (SimpleNamespace(),)
        if tracker_cfg is None:
            tracker_cfg = SimpleNamespace()
        if visualizer_cfg is None:
            visualizer_cfg = SimpleNamespace()
        if len(feature_extractor_cfgs) != len(class_ids):
            raise ValueError('Number of feature extractors must match length of class IDs')

        LOGGER.info('Loading detector model...')
        if self.detector_type == DetectorType.SSD:
            self.detector = SSDDetector(self.size, self.class_ids, **vars(ssd_detector_cfg))
        elif self.detector_type == DetectorType.YOLO:
            self.detector = YOLODetector(self.size, self.class_ids, **vars(yolo_detector_cfg))
        elif self.detector_type == DetectorType.PUBLIC:
            self.detector = PublicDetector(self.size, self.class_ids, self.detector_frame_skip,
                                           **vars(public_detector_cfg))

        LOGGER.info('Loading feature extractor models...')
        self.extractors = [FeatureExtractor(**vars(cfg)) for cfg in feature_extractor_cfgs]
        self.tracker = MultiTracker(self.size, self.extractors[0].metric, **vars(tracker_cfg))
        self.visualizer = Visualizer(**vars(visualizer_cfg))
        self.frame_count = 0

    def visible_tracks(self):
        """Retrieve visible tracks from the tracker

        Returns
        -------
        Iterator[Track]
            Confirmed and active tracks from the tracker.
        """
        return (track for track in self.tracker.tracks.values()
                if track.confirmed and track.active)

    def reset(self, cap_dt):
        """Resets multiple object tracker. Must be called before `step`.

        Parameters
        ----------
        cap_dt : float
            Time interval in seconds between each frame.
        """
        self.frame_count = 0
        self.tracker.reset(cap_dt)

    def step(self, frame):
        """Runs multiple object tracker on the next frame.

        Parameters
        ----------
        frame : ndarray
            The next frame.
        """
        detections = []
        if self.frame_count == 0:
            detections = self.detector(frame)
            self.tracker.init(frame, detections)
        elif self.frame_count % self.detector_frame_skip == 0:
            with Profiler('preproc'):
                self.detector.detect_async(frame)

            with Profiler('detect'):
                with Profiler('track'):
                    self.tracker.compute_flow(frame)
                detections = self.detector.postprocess()

            with Profiler('extract'):
                cls_bboxes = self._split_bboxes_by_cls(detections.tlbr, detections.label,
                                                       self.class_ids)
                for extractor, bboxes in zip(self.extractors, cls_bboxes):
                    extractor.extract_async(frame, bboxes)

                with Profiler('track', aggregate=True):
                    self.tracker.apply_kalman()

                embeddings = []
                for extractor in self.extractors:
                    embeddings.append(extractor.postprocess())
                embeddings = np.concatenate(embeddings) if len(embeddings) > 1 else embeddings[0]

            with Profiler('assoc'):
                self.tracker.update(self.frame_count, detections, embeddings)
        else:
            with Profiler('track'):
                self.tracker.track(frame)
        visible_tracks = list(self.visible_tracks())
        target = []
        target_bbox = []
        target_center_x = 0
        target_center_y = 0
        target_width = 0
        target_height=0
        target_accuracy=None
        if len(visible_tracks) > 0:
            max_hits =-1
            for visible_track in visible_tracks:
                bbox = visible_track.tlbr
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                hits = visible_track.hits * width * height / 1000 #hitlere bbox boyutunu ağırlık olarak verdim
                if hits > max_hits:
                    target = visible_track
                    target_bbox = bbox

                    max_hits= hits


            max_hits=-1

            target_center_x = ((target_bbox[0]+target_bbox[2])/2)
            target_center_y = ((target_bbox[1]+target_bbox[3])/2)
            target_width=target_bbox[2] - target_bbox[0]
            target_height=target_bbox[3] - target_bbox[1]

            if len(detections)>0:
                for detection in detections:
                    if detection[0].all() == target_bbox.all():
                        target_accuracy = round(detection[2]*100)
        if self.draw and len(target)>0:
            self._draw(frame, detections, target)
        self.frame_count += 1

        return target_center_x, target_center_y, target_width, target_height, target_accuracy


    @staticmethod
    def print_timing_info():
        LOGGER.debug('=================Timing Stats=================')
        LOGGER.debug(f"{'track time:':<37}{Profiler.get_avg_millis('track'):>6.3f} ms")
        LOGGER.debug(f"{'preprocess time:':<37}{Profiler.get_avg_millis('preproc'):>6.3f} ms")
        LOGGER.debug(f"{'detect/flow time:':<37}{Profiler.get_avg_millis('detect'):>6.3f} ms")
        LOGGER.debug(f"{'feature extract/kalman filter time:':<37}"
                     f"{Profiler.get_avg_millis('extract'):>6.3f} ms")
        LOGGER.debug(f"{'association time:':<37}{Profiler.get_avg_millis('assoc'):>6.3f} ms")

    @staticmethod
    @nb.njit(cache=True)
    def _split_bboxes_by_cls(bboxes, labels, class_ids):
        cls_bboxes = []
        begin = 0
        for cls_id in class_ids:
            end = bisect_right(labels, cls_id, begin)
            cls_bboxes.append(bboxes[begin:end])
            begin = end
        return cls_bboxes

    def _draw(self, frame, detections, target):
        visible_tracks = list(self.visible_tracks())
        self.visualizer.render(frame, target, detections, self.tracker.klt_bboxes.values(),
                               self.tracker.flow.prev_bg_keypoints, self.tracker.flow.bg_keypoints)
        cv2.putText(frame, f'visible: {len(visible_tracks)}', (30, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2, cv2.LINE_AA)
