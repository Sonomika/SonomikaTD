# Human/Object Tracker model

This effect uses the TensorFlow Object Detection API's SSD MobileNet V1 COCO model through OpenCV DNN.

- Model: `ssd_mobilenet_v1_coco_2017_11_17`
- Source: http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v1_coco_2017_11_17.tar.gz
- OpenCV graph configuration derived from: https://gist.github.com/dkurt/45118a9c57c38677b65d6953ae62924a
- Dataset classes: COCO

The model is bundled so Sonomika users do not need to install an additional Python ML package.

Face mode uses OpenCV Zoo's YuNet face detector:
https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
