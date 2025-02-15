# YOLOv5 🚀 by Ultralytics, GPL-3.0 license
"""
Run inference on images, videos, directories, streams, etc.

Usage - sources:
    $ python path/to/detect.py --weights yolov5s.pt --source 0              # webcam
                                                             img.jpg        # image
                                                             vid.mp4        # video
                                                             path/          # directory
                                                             path/*.jpg     # glob
                                                             'https://youtu.be/Zgi9g1ksQHc'  # YouTube
                                                             'rtsp://example.com/media.mp4'  # RTSP, RTMP, HTTP stream

Usage - formats:
    $ python path/to/detect.py --weights yolov5s.pt                 # PyTorch
                                         yolov5s.torchscript        # TorchScript
                                         yolov5s.onnx               # ONNX Runtime or OpenCV DNN with --dnn
                                         yolov5s.xml                # OpenVINO
                                         yolov5s.engine             # TensorRT
                                         yolov5s.mlmodel            # CoreML (MacOS-only)
                                         yolov5s_saved_model        # TensorFlow SavedModel
                                         yolov5s.pb                 # TensorFlow GraphDef
                                         yolov5s.tflite             # TensorFlow Lite
                                         yolov5s_edgetpu.tflite     # TensorFlow Edge TPU
"""

import argparse
import os
import sys
from pathlib import Path
import pandas as pd  #added for store the partials counts of the inferences
import numpy as np   #added for interpolate data from the gps data
import math


import torch
import torch.backends.cudnn as cudnn

def slope(p1,p2):
    x1,y1=p1
    x2,y2=p2
    if x2!=x1:
        return((y2-y1)/(x2-x1))
    else:
        return 'NA'

def drawLine_2(image,p1,p2):
    x1,y1=p1
    x2,y2=p2
    ### finding slope
    m=slope(p1,p2)
    ### getting image shape
    h,w=image.shape[:2]

    if m!='NA':
        ### here we are essentially extending the line to x=0 and x=width
        ### and calculating the y associated with it
        ##starting point
        px=0
        py=-(x1-0)*m+y1
        ##ending point
        qx=w
        qy=-(x2-w)*m+y2
    else:
    ### if slope is zero, draw a line with x=x1 and y=0 and y=height
        px,py=x1,0
        qx,qy=x1,h
    cv2.line(image, (int(px), int(py)), (int(qx), int(qy)), (0, 0, 255), 2)
    return image

def drawLine(image,p1,p2):
    x1,y1=p1
    x2,y2=p2
    ### finding slope
    m=slope(p1,p2)
    ### getting image shape
    h,w=image.shape[:2]

    if m!='NA':
        ### here we are essentially extending the line to x=0 and x=width
        ### and calculating the y associated with it
        ##starting point
        px=0
        py=-(x1-0)*m+y1
        ##ending point
        qx=w
        qy=-(x2-w)*m+y2
    else:
    ### if slope is zero, draw a line with x=x1 and y=0 and y=height
        px,py=x1,0
        qx,qy=x1,h
    cv2.line(image, (int(px), int(py)), (int(qx), int(qy)), (0, 255, 0), 2)
    return image
#count vains 
def count_vains(x_lim,x_measured,vains, w_size, im, center_coordinates, xyxy):
    if abs(x_lim-x_measured)<=w_size: #15 por defecto
        color = (0, 255, 0)
        thickness=-1
        radius = 5
        cv2.circle(im, center_coordinates, radius, color, thickness)
        annotator = Annotator(im, line_width=thickness, example='')
        annotator.box_label(xyxy, 'h', color=256)
        vains=vains+1;
        return vains
    else:
        return vains
    
def measure_area(x_lim,x_measured,A_one_box, i_area):
    if abs(x_lim-x_measured)<=35:
        i_area=i_area+1
        return A_one_box, i_area
    else:
        return 0, i_area  
def measure_distance(lat1,lon1,lat2,lon2):
    # approximate radius of earth in km
    R = 6373.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance
def count_seeds(x_lim,x_measured,seeds,quantity, w_size):
    if abs(x_lim-x_measured)<=w_size:  #15
        if quantity==1:
            seeds=seeds+1;
        if quantity==2:
            seeds=seeds+2;
        if quantity==3:
            seeds=seeds+3;    
        return seeds
    else:
        return seeds

def count_seeds_type(x_lim,x_measured,seeds_1,seeds_2,seeds_3,seeds_4,quantity,w_size):
    if abs(x_lim-x_measured)<=w_size:   #15
        if quantity==1:
            seeds_1=seeds_1+1;
            return seeds_1, seeds_2, seeds_3, seeds_4
        if quantity==2:
            seeds_2=seeds_2+1;
            return seeds_1, seeds_2, seeds_3, seeds_4
        if quantity==3:
            seeds_3=seeds_3+1;
            return seeds_1, seeds_2, seeds_3, seeds_4
        if quantity==4:
            seeds_4=seeds_4+1; 
            return seeds_1, seeds_2, seeds_3, seeds_4   
    else:
        return seeds_1, seeds_2, seeds_3, seeds_4
    


FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from models.common import DetectMultiBackend
from utils.datasets import IMG_FORMATS, VID_FORMATS, LoadImages, LoadStreams
from utils.general import (LOGGER, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_coords, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, time_sync


@torch.no_grad()
def run(weights=ROOT / 'yolov5s.pt',  # model.pt path(s)
        source=ROOT / 'data/images',  # file/dir/URL/glob, 0 for webcam
        data=ROOT / 'data/coco128.yaml',  # dataset.yaml path
        imgsz=(640, 640),  # inference size (height, width)
        conf_thres=0.25,  # confidence threshold
        iou_thres=0.45,  # NMS IOU threshold
        max_det=1000,  # maximum detections per image
        device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        view_img=False,  # show results
        save_txt=False,  # save results to *.txt
        save_conf=False,  # save confidences in --save-txt labels
        save_crop=False,  # save cropped prediction boxes
        nosave=False,  # do not save images/videos
        classes=None,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        visualize=False,  # visualize features
        update=False,  # update all models
        project=ROOT / 'runs/detect',  # save results to project/name
        name='exp',  # save results to project/name
        exist_ok=False,  # existing project/name ok, do not increment
        line_thickness=1,  # bounding box thickness (pixels)
        hide_labels=False,  # hide labels
        hide_conf=False,  # hide confidences
        half=False,  # use FP16 half-precision inference
        dnn=False,  # use OpenCV DNN for ONNX inference
        ):
    source = str(source)
    save_img = not nosave and not source.endswith('.txt')  # save inference images
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
    is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
    webcam = source.isnumeric() or source.endswith('.txt') or (is_url and not is_file)
    if is_url and is_file:
        source = check_file(source)  # download

    # Directories
    save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # increment run
    (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # check image size
    #-------------------------------------------------------
    #variables adicionales GBOT
    vains=0 #initial number of vains for each detection
    A=0
    i_area=0 #numero de iteraciones
    w_size=15 #ancho default
    thersold=12 #cantidad de frames que aparece la franja secundaria si hay obstruccion
    column_names = ["vainas", "seeds", "seeds_1", "seeds_2", "seeds_3", "seeds_4", "area", "i_area", "frame", "robot_speed_", "distance_plot"]
    cum_sum_ = pd.DataFrame(columns=column_names)
    #--------------------------------------------------------
    # Dataloader
    if webcam:
        view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt)
        bs = len(dataset)  # batch_size
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt)
        bs = 1  # batch_size
    vid_path, vid_writer = [None] * bs, [None] * bs

    # Run inference
    area=0
    vainas=0
    seeds=0
    seeds_1=0
    seeds_2=0
    seeds_3=0
    seeds_4=0
    model.warmup(imgsz=(1 if pt else bs, 3, *imgsz))  # warmup
    dt, seen = [0.0, 0.0, 0.0], 0
    csv_file="/content/yolov5/videos/"+(Path(dataset.files[0]).name).split(".mp4")[0]+".csv"
    #csv_file=(Path(dataset.files[0]).name).split(".mp4")[0]+".csv"
    print("processing: " + "/content/yolov5/videos"+ csv_file) ##agregue esto para identificar el nombre del video
    csv_pd = pd.read_csv(csv_file)
    for path, im, im0s, vid_cap, s in dataset:
        #############Seguir trabajando aca para hallar el nombre del video
        t1 = time_sync()
        im = torch.from_numpy(im).to(device)
        im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
        im /= 255  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim
        t2 = time_sync()
        dt[0] += t2 - t1

        # Inference
        visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
        pred = model(im, augment=augment, visualize=visualize)
        t3 = time_sync()
        dt[1] += t3 - t2

        # NMS
        pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)
        dt[2] += time_sync() - t3

        # Second-stage classifier (optional)
        # pred = utils.general.apply_classifier(pred, classifier_model, im, im0s)

        # Process predictions
        for i, det in enumerate(pred):  # per image
            seen += 1
            if webcam:  # batch_size >= 1
                p, im0, frame = path[i], im0s[i].copy(), dataset.count
                s += f'{i}: '
            else:
                p, im0, frame = path, im0s.copy(), getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # im.jpg
            txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # im.txt
            s += '%gx%g ' % im.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0.copy() if save_crop else im0  # for save_crop
            annotator = Annotator(im0, line_width=line_thickness, example=str(names))
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Write results
                ############ extraccion dato de velocidad####################
                print(frame)
                robot_speed_=np.interp(frame/10, csv_pd['duration_video'], csv_pd['vel'])
                print(robot_speed_)
                ##############################################################
                
                ############ calculo de distancia############################
                
                lat1=csv_pd['latitude'].min()
                lon1=csv_pd['longitude'].min()
                lat2=np.interp(frame/10, csv_pd['duration_video'], csv_pd['latitude'])
                lon2=np.interp(frame/10, csv_pd['duration_video'], csv_pd['longitude'])
                distance_plot=1000*measure_distance(lat1,lon1,lat2,lon2)
                print(distance_plot)
                ##############################################################
                
                for *xyxy, conf, cls in reversed(det):
                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * len(line)).rstrip() % line + '\n')
                    if save_img or save_crop or view_img:  # Add bbox to image
                        c = int(cls)  # integer class
                        center_coordinates=((xyxy[2]+int((xyxy[0]-xyxy[2])/2)),(xyxy[3]+int((xyxy[1]-xyxy[3])/2)))
                        A_one_box=int((xyxy[0]-xyxy[2])/2) #ancho/2 del box
                        color = (255, 0, 0)
                        thickness=-1
                        radius = 5
                        #label='v'
                        cv2.circle(im0, center_coordinates, radius, color, thickness)  #circle over the leaf
                        label = None if hide_labels else (names[c] if hide_conf else f'{names[c]} {conf:.2f}')
                        annotator.box_label(xyxy, label, color=colors(c, True))
                        vainas=count_vains(center_coordinates[0],600,vainas, 10*(robot_speed_)*int(abs(w_size)), im0, center_coordinates, xyxy)
                        if label=='uno':
                            seeds=count_seeds(center_coordinates[0],600,seeds,1,10*(robot_speed_)*int(abs(w_size)))
                            seeds_1, seeds_2, seeds_3, seeds_4=count_seeds_type(center_coordinates[0],600,seeds_1,seeds_2,seeds_3,seeds_4,1,10*(robot_speed_)*int(abs(w_size)))
                            color = (255, 0, 0)
                            annotator.box_label(xyxy, 'x1', color=colors(c, True))
                        if label=='dos':
                            seeds=count_seeds(center_coordinates[0],600,seeds,2,10*(robot_speed_)*int(abs(w_size)))
                            seeds_1, seeds_2, seeds_3, seeds_4=count_seeds_type(center_coordinates[0],600,seeds_1,seeds_2,seeds_3,seeds_4,2,10*(robot_speed_)*int(abs(w_size)))
                            color = (0, 255, 0)
                            annotator.box_label(xyxy, 'x2', color=colors(c, True))
                        if label=='tres':
                            seeds=count_seeds(center_coordinates[0],600,seeds,3,10*(robot_speed_)*int(abs(w_size)))
                            seeds_1, seeds_2, seeds_3, seeds_4=count_seeds_type(center_coordinates[0],600,seeds_1,seeds_2,seeds_3,seeds_4,3,10*(robot_speed_)*int(abs(w_size)))
                            color = (0, 0, 255)
                            annotator.box_label(xyxy, 'x3', color=colors(c, True))
                        if label=='cuatro':
                            seeds=count_seeds(center_coordinates[0],600,seeds,4,10*(robot_speed_)*int(abs(w_size)))
                            seeds_1, seeds_2, seeds_3, seeds_4=count_seeds_type(center_coordinates[0],600,seeds_1,seeds_2,seeds_3,seeds_4,4,10*(robot_speed_)*int(abs(w_size)))
                            color = (255, 255, 0)
                            annotator.box_label(xyxy, 'x4', color=colors(c, True))
                        res1, res2=measure_area(center_coordinates[0],600,A_one_box, i_area)
                        area=area+res1
                        i_area=res2
                        font = cv2.FONT_HERSHEY_SIMPLEX 
                        if save_crop:
                            save_one_box(xyxy, imc, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)
                cv2.putText(im0, str('Seeds_Count: ' + str(round(seeds,0))), (0,90), font, 1, (255, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(im0, str('Pods_1_Count: ' + str(round(seeds_1,0))), (0,130), font, 1, (255, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(im0, str('Pods_2_Count: ' + str(round(seeds_2,0))), (0,170), font, 1, (255, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(im0, str('Pods_3_Count: ' + str(round(seeds_3,0))), (0,210), font, 1, (255, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(im0, str('Pods_4_Count: ' + str(round(seeds_4,0))), (0,250), font, 1, (255, 0, 0), 2, cv2.LINE_AA)
                if i_area!=0:
                     area=area/i_area #area promedio dentro de la franja por frame
                else:
                    area=0
                cum_sum_.loc[len(cum_sum_)] = [vainas, seeds, seeds_1, seeds_2, seeds_3, seeds_4, area, i_area, frame, robot_speed_, distance_plot]
                w_size=area
                area=0
                i_area=0
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(im0, str('Pods Count: ' + str(round(vainas,0))), (0,50), font, 1, (255, 0, 0), 2, cv2.LINE_AA)
            drawLine(im0,(600-10*robot_speed_*w_size,0),(600-10*robot_speed_*w_size,240))  #camara ELP a 35cm del cultivo #585
            drawLine(im0,(600+10*robot_speed_*w_size,0),(600+10*robot_speed_*w_size,240))  #615
            if vainas==0:
                cum_sum_.loc[len(cum_sum_)] = [vainas, seeds, seeds_1, seeds_2, seeds_3, seeds_4, area, i_area, frame, robot_speed_, distance_plot]
            cum_sum_.to_csv(save_path+'.csv', index=False, mode='w+')

            # Stream results
            im0 = annotator.result()
            if view_img:
                cv2.imshow(str(p), im0)
                cv2.waitKey(1)  # 1 millisecond

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'image':
                    cv2.imwrite(save_path, im0)
                else:  # 'video' or 'stream'
                    if vid_path[i] != save_path:  # new video
                        vid_path[i] = save_path
                        if isinstance(vid_writer[i], cv2.VideoWriter):
                            vid_writer[i].release()  # release previous video writer
                        if vid_cap:  # video
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        else:  # stream
                            fps, w, h = 30, im0.shape[1], im0.shape[0]
                        save_path = str(Path(save_path).with_suffix('.mp4'))  # force *.mp4 suffix on results videos
                        vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                    vid_writer[i].write(im0)

        # Print time (inference-only)
        LOGGER.info(f'{s}Done. ({t3 - t2:.3f}s)')

    # Print results
    t = tuple(x / seen * 1E3 for x in dt)  # speeds per image
    LOGGER.info(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}' % t)
    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
        LOGGER.info(f"Results saved to {colorstr('bold', save_dir)}{s}")
    if update:
        strip_optimizer(weights)  # update model (to fix SourceChangeWarning)


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default=ROOT / 'yolov5s.pt', help='model path(s)')
    parser.add_argument('--source', type=str, default=ROOT / 'data/images', help='file/dir/URL/glob, 0 for webcam')
    parser.add_argument('--data', type=str, default=ROOT / 'data/coco128.yaml', help='(optional) dataset.yaml path')
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], help='inference size h,w')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='NMS IoU threshold')
    parser.add_argument('--max-det', type=int, default=1000, help='maximum detections per image')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='show results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--save-crop', action='store_true', help='save cropped prediction boxes')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --classes 0, or --classes 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--visualize', action='store_true', help='visualize features')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default=ROOT / 'runs/detect', help='save results to project/name')
    parser.add_argument('--name', default='exp', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--line-thickness', default=3, type=int, help='bounding box thickness (pixels)')
    parser.add_argument('--hide-labels', default=False, action='store_true', help='hide labels')
    parser.add_argument('--hide-conf', default=False, action='store_true', help='hide confidences')
    parser.add_argument('--half', action='store_true', help='use FP16 half-precision inference')
    parser.add_argument('--dnn', action='store_true', help='use OpenCV DNN for ONNX inference')
    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand
    print_args(FILE.stem, opt)
    return opt


def main(opt):
    check_requirements(exclude=('tensorboard', 'thop'))
    run(**vars(opt))


if __name__ == "__main__":
    opt = parse_opt()
    main(opt)
