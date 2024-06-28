import cv2
import numpy as np
from moviepy.editor import *

global Fps

def crop_to_vertical(input_video_path, output_video_path):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    cap = cv2.VideoCapture(input_video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    vertical_height = original_height
    vertical_width = int(vertical_height * 9 / 16)
    print(vertical_height, vertical_width)


    if original_width < vertical_width:
        print("Error: Original video width is less than the desired vertical width.")
        return

    x_start = (original_width - vertical_width) // 2
    x_end = x_start + vertical_width
    print(f"start and end - {x_start} , {x_end}")
    print(x_end-x_start)
    half_width = vertical_width // 2

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (vertical_width, vertical_height))
    global Fps
    Fps = fps
    print(fps)
    count = 0
    for _ in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            centerX = x+(w//2)
            # print(centerX)
            
            if x_start - (centerX - half_width) <100 :
                ## IF dif from prev fram is low then no movment is done
                pass #use prev vals
            else:
                x_start = centerX - half_width
                x_end = centerX + half_width


                if int(cropped_frame.shape[1]) != x_end- x_start:
                    if x_end < original_width:
                        x_end += int(cropped_frame.shape[1]) - (x_end-x_start)
                        if x_end > original_width:
                            x_start -= int(cropped_frame.shape[1]) - (x_end-x_start)
                    else:
                        x_start -= int(cropped_frame.shape[1]) - (x_end-x_start)
                        if x_start < 0:
                            x_end += int(cropped_frame.shape[1]) - (x_end-x_start)
                    print("Frame size inconsistant")
                    print(x_end- x_start)

        count += 1
        cropped_frame = frame[:, x_start:x_end]
        if cropped_frame.shape[1] == 0:
            x_start = (original_width - vertical_width) // 2
            x_end = x_start + vertical_width
            cropped_frame = frame[:, x_start:x_end]
        
        print(cropped_frame.shape)

        out.write(cropped_frame)

    cap.release()
    out.release()
    print("Cropping complete. The video has been saved to", output_video_path, count)



def combine_videos(video_with_audio, video_without_audio, output_filename):
    try:
        # Load video clips
        clip_with_audio = VideoFileClip(video_with_audio)
        clip_without_audio = VideoFileClip(video_without_audio)

        audio = clip_with_audio.audio

        combined_clip = clip_without_audio.set_audio(audio)

        global Fps
        combined_clip.write_videofile(output_filename, codec='libx264', audio_codec='aac', fps=Fps, preset='medium', bitrate='3000k')
        print(f"Combined video saved successfully as {output_filename}")
    
    except Exception as e:
        print(f"Error combining video and audio: {str(e)}")


def crop_to_vertical2(input_video_path, output_video_path):
    # Open the video file
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    # Get original video properties
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate the size of the cropped frame
    vertical_height = original_height
    vertical_width = int(vertical_height * 9 / 16)
    print(f"Vertical dimensions: {vertical_width}x{vertical_height}")

    # Ensure the original video width is greater than the desired vertical width
    if original_width < vertical_width:
        print("Error: Original video width is less than the desired vertical width.")
        return

    # Calculate the initial cropping parameters to center the crop
    x_start = (original_width - vertical_width) // 2
    x_end = x_start + vertical_width
    print(f"Initial crop window: {x_start} to {x_end}")

    half_width = vertical_width // 2

    # Define the codec and create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # Changed to H.264 codec
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (vertical_width, vertical_height))

    # Variables for smooth transitions and frame comparison
    prev_x_start = x_start
    prev_x_end = x_end
    smoothing_factor = 0.1
    movement_threshold = vertical_width * 0.05  # 5% of frame width
    prev_frame = None

    count = 0
    for _ in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        # Face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            centerX = x + (w // 2)

            # Calculate new crop window
            new_x_start = centerX - half_width
            new_x_end = centerX + half_width

            # Check if movement exceeds threshold
            if abs(new_x_start - prev_x_start) > movement_threshold:
                # Apply smooth transition
                x_start = int(prev_x_start + smoothing_factor * (new_x_start - prev_x_start))
                x_end = int(prev_x_end + smoothing_factor * (new_x_end - prev_x_end))

                # Ensure x_start and x_end are within frame bounds
                x_start = max(0, min(original_width - vertical_width, x_start))
                x_end = min(original_width, max(vertical_width, x_end))

                prev_x_start = x_start
                prev_x_end = x_end

        # Crop the frame
        cropped_frame = frame[:, x_start:x_end]

        # Check if the frame is significantly different from the previous one
        if prev_frame is None or np.mean(cv2.absdiff(cropped_frame, prev_frame)) > 1.0:
            out.write(cropped_frame)
            prev_frame = cropped_frame
            count += 1

    # Release the video objects
    cap.release()
    out.release()
    print(f"Cropping complete. The video has been saved to {output_video_path}")
    print(f"Processed {count} frames out of {total_frames}")


if __name__ == "__main__":
    input_video_path = r'Short.mp4'
    output_video_path = 'Croped_output_video.mp4'
    final_video_path = 'final_video_with_audio.mp4'
    crop_to_vertical(input_video_path, output_video_path)
    combine_videos(input_video_path, output_video_path, final_video_path)



