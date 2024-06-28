import cv2
import numpy as np
#Face Detection function
def detect_faces(video_file):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Load the video
    cap = cv2.VideoCapture(video_file)

    faces = []

    # Detect and store unique faces
    while len(faces) < 5:
        ret, frame = cap.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected_faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            # Iterate through the detected faces
            for face in detected_faces:
                # Check if the face is already in the list of faces
                if not any(np.array_equal(face, f) for f in faces):
                    faces.append(face)

            # Print the number of unique faces detected so far
            print(f"Number of unique faces detected: {len(faces)}")

    # Release the video capture object
    cap.release()

    # If faces detected, return the list of faces
    if len(faces) > 0:
        return faces
    
def crop_video(faces, input_file, output_file):
    try:
        if len(faces) > 0:
            # Constants for cropping
            CROP_RATIO = 0.9  # Adjust the ratio to control how much of the face is visible in the cropped video
            VERTICAL_RATIO = 9 / 16  # Aspect ratio for the vertical video

            # Read the input video
            cap = cv2.VideoCapture(input_file)

            # Get the frame dimensions
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Calculate the target width and height for cropping (vertical format)
            target_height = int(frame_height * CROP_RATIO)
            target_width = int(target_height * VERTICAL_RATIO)

            # Create a VideoWriter object to save the output video
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            output_video = cv2.VideoWriter(output_file, fourcc, 30.0, (target_width, target_height))

            # Loop through each frame of the input video
            while True:
                ret, frame = cap.read()

                # If no more frames, break out of the loop
                if not ret:
                    break

                # Iterate through each detected face
                for face in faces:
                    # Unpack the face coordinates
                    x, y, w, h = face

                    # Calculate the crop coordinates
                    crop_x = max(0, x + (w - target_width) // 2)  # Adjust the crop region to center the face
                    crop_y = max(0, y + (h - target_height) // 2)
                    crop_x2 = min(crop_x + target_width, frame_width)
                    crop_y2 = min(crop_y + target_height, frame_height)

                    # Crop the frame based on the calculated crop coordinates
                    cropped_frame = frame[crop_y:crop_y2, crop_x:crop_x2]

                    # Resize the cropped frame to the target dimensions
                    resized_frame = cv2.resize(cropped_frame, (target_width, target_height))

                    # Write the resized frame to the output video
                    output_video.write(resized_frame)

            cap.release()
            output_video.release()

            print("Video cropped successfully.")
        else:
            print("No faces detected in the video.")
    except Exception as e:
        print(f"Error during video cropping: {str(e)}")


    return None
if __name__ == "__main__":
    input = r"Short.mp4"
    faces = detect_faces(input)
    print(faces)
    crop_video(faces, input, "Cropped.mp4")
    print("DONE")

    