import os
path = os.path.abspath(os.getcwd()) 
path=path+"/videos"
for f in os.listdir(path):
    i, ext = os.path.splitext(f)
    file=i+ext
    if ext == '.mp4':
        python /content/yolov5/detect.py --weights /content/yolov5/soja.pt --img 1280 --conf 0.1 --iou-thres 0.35 --exist-ok --source videos/$file  #segunda siembra
        #!python ./yolo_contador/yolov5/detect_one_band.py --weights ./yolo_contador/yolov5/runs/train/exp/weights/soja.pt --img 1280 --conf 0.4 --iou-thres 0.35 --exist-ok --source videos/$file  #tercer siembra
        #!python ./yolo_contador/yolov5/detect_one_band.py --weights ./yolo_contador/yolov5/runs/train/exp/weights/soja.pt --img 1280 --conf 0.3 --iou-thres 0.35 --exist-ok --source videos/$file  #cuarta siembra lejos
        #!python ./yolo_contador/yolov5/detect_one_band.py --weights ./yolo_contador/yolov5/runs/train/exp/weights/soja.pt --img 1280 --conf 0.5 --iou-thres 0.35 --exist-ok --source videos/$file
        #!python ./yolo_contador/yolov5/detect_one_band.py --weights ./yolo_contador/yolov5/runs/train/exp/weights/vainas_verdes.pt --img 1024 --conf 0.1 --iou-thres 0.2 --exist-ok --source videos/$file           #modelo vainas verdes
        #!python ./yolo_contador/yolov5/detect_one_band.py --weights ./yolo_contador/yolov5/runs/train/exp/weights/pablo_vaina_verde.pt --img 1024 --conf 0.2 --iou-thres 0.45 --exist-ok --source videos/$file           #modelo vainas verdes
cp ./runs/detect/exp/*.mp4 ./inferencias
cp ./runs/detect/exp/*.csv ./inferencias
!rm -r ./runs