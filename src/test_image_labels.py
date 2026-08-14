import cv2
import os
import random

def visualize_yolo_labels(images_dir, labels_dir, class_names, num_samples=1):
    image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    samples = random.sample(image_files, min(num_samples, len(image_files)))

    for img_name in samples:
        img_path = os.path.join(images_dir,img_name)
        label_path = os.path.join(labels_dir,os.path.splitext(img_name)[0]+'.txt')

        img = cv2.imread(img_path)
        h, w = img.shape[:2]

        if not os.path.exists(label_path):
            print(f"Ingen label-fil for {img_name} - hopper over denne")
            continue

        with open(label_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            cls_id, x_center, y_center, box_w, box_h = int(parts[0]), *map(float,parts[1:5])

            #Konverter fra normalisert YOLO-format til pikselkoordinater
            x_center_px = x_center * w
            y_center_px = y_center * h
            box_w_px = box_w * w
            box_h_px = box_h * h

            x1 = int(x_center_px - box_w_px/2)
            y1 = int(y_center_px - box_h_px/2)
            x2 = int(x_center_px + box_w_px/2)
            y2 = int(y_center_px + box_h_px/2)

            label = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
            cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,0),2)
            cv2.putText(img, label, (x1,y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0),2)

        cv2.imshow(f"Sjekk: {img_name}", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


#ta i bruk 
class_names = ["Ditt objekt"]

visualize_yolo_labels(
    images_dir="Q:\SYNTH-DATASET\output\coco_data\images",
    labels_dir="Q:\SYNTH-DATASET\output\coco_data\labels",
    class_names=class_names,
    num_samples=1
)
