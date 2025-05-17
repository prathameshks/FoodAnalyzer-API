import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
import os


# Load the model from TF Hub
# Cache the model globally
detector = hub.load("https://tfhub.dev/google/openimages_v4/ssd/mobilenet_v2/1").signatures['default']

# Classes you care about
TARGET_CLASSES = set(["Food processor", "Fast food", "Food", "Seafood", "Snack"])

UPLOADED_IMAGES_DIR = "uploaded_images"
if not os.path.exists(UPLOADED_IMAGES_DIR):
    os.makedirs(UPLOADED_IMAGES_DIR)


def load_image_from_url(url, size=(640, 480)):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert("RGB")
    img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    return img


def run_object_detection(image: Image.Image):
    image_np = np.array(image)
    # Convert to tensor without specifying dtype
    input_tensor = tf.convert_to_tensor(image_np)[tf.newaxis, ...]
    # Convert to float32 and normalize to [0,1]
    input_tensor = tf.cast(input_tensor, tf.float32) / 255.0
    results = detector(input_tensor)
    results = {k: v.numpy() for k, v in results.items()}
    return results, image_np

def get_filtered_class_boxes(results):
    # for same class, keep the one with the highest score
    # and remove duplicates
    boxes = []
    classes = []
    scores = []

    for i in range(len(results["detection_scores"])):
        class_name = results["detection_class_entities"][i].decode("utf-8")
        box = results["detection_boxes"][i]
        score = results["detection_scores"][i]
        if class_name in TARGET_CLASSES:
            if class_name not in classes:
                boxes.append(box)
                classes.append(class_name)
                scores.append(score)
            else:
                index = classes.index(class_name)
                if score > scores[index]:
                    boxes[index] = box
                    classes[index] = class_name
                    scores[index] = score
    return boxes, classes, scores


def crop_and_save(image_np, boxes, class_names, scores, min_score=0.3):
    cropped_images = []
    for i in range(len(scores)):
        if scores[i] > min_score:
            ymin, xmin, ymax, xmax = boxes[i]
            im_width, im_height = image_np.shape[1], image_np.shape[0]
            (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                          ymin * im_height, ymax * im_height)
            cropped_image = image_np[int(top):int(bottom), int(left):int(right)]
            cropped_images.append((cropped_image, class_names[i], scores[i]))
            # Save the cropped image
            pil_image = Image.fromarray(cropped_image)
            pil_image.save(os.path.join(UPLOADED_IMAGES_DIR, f"{class_names[i]}_{scores[i]:.2f}.jpg"))
    return cropped_images

def draw_boxes(image_np, boxes, class_names, scores, min_score=0.3):
    image_pil = Image.fromarray(image_np)
    draw = ImageDraw.Draw(image_pil)
    font = ImageFont.load_default()

    for i in range(len(scores)):
        label = class_names[i]
        if label in TARGET_CLASSES and scores[i] > min_score:
            ymin, xmin, ymax, xmax = boxes[i]
            im_width, im_height = image_pil.size
            (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                          ymin * im_height, ymax * im_height)
            draw.rectangle([left, top, right, bottom], outline="red", width=2)
            draw.text((left, top), f"{label}: {scores[i]*100:.1f}%", fill="white", font=font)
    return image_pil