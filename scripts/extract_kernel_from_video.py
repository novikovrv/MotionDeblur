import argparse
import cv2
import numpy as np
from scipy.signal import correlate2d
from datetime import datetime, timedelta

def find_similar_blocks(img1, img2, block_size=100, w_size = 120):
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    # Проверяем, что размер блока не превышает размер изображений
    if block_size*2 > min(h1, w1, h2, w2):
        raise ValueError("Размер блока не должен превышать размер изображений")

    # Вычисляем координаты центрального блока в img1
    center_x = w1 // 2
    center_y = h1 // 2
    center_block = img1[center_y-block_size:center_y+block_size, center_x-block_size:center_x+block_size]

    # Вычисляем координаты центральной области в img2
    center_x2 = w2 // 2
    center_y2 = h2 // 2
    start_x2 = center_x2 - w_size
    start_y2 = center_y2 - w_size
    end_x2 = center_x2 + w_size
    end_y2 = center_y2 + w_size
    center_region = img2[start_y2:end_y2, start_x2:end_x2]

    # Находим наиболее похожий блок в center_region
    min_diff = -2
    #best_offset = (0, 0)
    for y2 in range(block_size, center_region.shape[0] - block_size + 1, 1):
        for x2 in range(block_size, center_region.shape[1] - block_size + 1, 1):
            block2 = center_region[y2-block_size:y2+block_size, x2-block_size:x2+block_size]
            corr = np.corrcoef(center_block.flatten(), block2.flatten())[0, 1]
            #print(corr)
            if corr > min_diff:
                min_diff = corr
                best_offset = (x2 - center_x + start_x2, y2 - center_y + start_y2)

    return [best_offset]

def extract_frames(video_capture, start_time, end_time):
    frames = []

    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        current_time = video_capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if start_time <= current_time <= end_time:
            frames.append(frame)
        if current_time > end_time:
            break
    video_capture.release()


    return frames

def kernel_points(frames):
    first = frames[0]
    first = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
    coords = []
    for i in range(4, len(frames), 10):
        frame = frames[i]
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        coords.append(find_similar_blocks(first, frame, 100, 150))
        first = frame
    return coords


def mat_array_normalization(array_of_matrix):
    normalized_matrix = np.empty_like(array_of_matrix, dtype=np.float32)
    for i in range(array_of_matrix.shape[0]):
        matr = array_of_matrix[i]
        sum_values = np.sum(matr)
        if sum_values != 0:
            normalized_matrix[i] = matr.astype(np.float32) / sum_values
        else:
            normalized_matrix[i] = matr.astype(np.float32)
    return normalized_matrix

def mat_sum(array_of_matrix):
    sum_matrix = np.sum(array_of_matrix, axis=0)
    return sum_matrix


def draw_line(matr, x = (1, 9), y = (8, 2), width = 1):
    cv2.line(matr, x, y, 255, width, lineType=cv2.LINE_AA)
    return matr


def draw_coordinates(image_array,center_x, center_y, a, width):
    count_iter = 0
    for shift in a:
        x, y = shift[0]
        end_x = center_x + x
        end_y = center_y + y
        x1 = (center_x, center_y)
        y1 = (end_x, end_y)
        image_array[count_iter] = draw_line(image_array[count_iter], x1, y1, width)
        print(center_x, center_y, end_x, end_y)
        center_x = end_x
        center_y = end_y
        count_iter += 1
    return image_array


parser = argparse.ArgumentParser()
parser.add_argument('--video_path', required=True)
parser.add_argument('--image_time', required=True)
parser.add_argument('--end_video_time', required=True)
parser.add_argument('--exp_time', required=True)
parser.add_argument('--kernel_size', required=True)
parser.add_argument('--kernel_width', default=1)
if __name__ == '__main__':

    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count/fps

    image_time = datetime.strptime(args.image_time, "%H:%M:%S.%f")
    video_end_time = datetime.strptime(args.end_video_time, "%H:%M:%S.%f")
    video_start_time = (video_end_time - timedelta(seconds=duration))

    start_frame_time = (image_time - video_start_time).total_seconds()
    end_frame_time = start_frame_time + float(args.exp_time)

    selected_frames = extract_frames(cap, start_frame_time, end_frame_time)
    coords = kernel_points(selected_frames)
    kernel_size = int(args.kernel_size)
    array_of_matrix = np.zeros((len(coords), kernel_size, kernel_size), dtype=np.uint8)
    k = draw_coordinates(array_of_matrix, kernel_size // 2, kernel_size // 2, coords, int(args.kernel_width))
    k = mat_array_normalization(k)
    kernel = mat_sum(k)

    cv2.imwrite('kernel.png', kernel * 1500.0)


