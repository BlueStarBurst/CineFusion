import socket
import cv2
import struct
import numpy as np
import threading

def display_frames(original_frame, modified_frame):
    cv2.imshow("Original Frame", original_frame)
    cv2.imshow("Modified Frame", modified_frame)
    key = cv2.waitKey(1)
    if key == ord('q'):
        return False
    return True

def sendAndReceiveFrames():
    webcamSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    webcamServerAddress = ('127.0.0.1', 12345)
    webcamSocket.connect(webcamServerAddress)

    cap = cv2.VideoCapture(0)

    while True:
        # Capture frame from webcam
        ret, frame = cap.read()
        if not ret:
            break

        # Convert frame to JPEG format
        _, frame_data = cv2.imencode('.jpg', frame)

        # Get the size of the frame data
        frame_size = len(frame_data)

        # Pack the size of the frame data as a 4-byte integer
        size_data = struct.pack("I", frame_size)

        # Send the size of the frame data to the server
        webcamSocket.sendall(size_data)

        # Send the frame data to the server
        webcamSocket.sendall(frame_data)

        # Receive the size of the modified frame data from the server
        size_data = webcamSocket.recv(4)
        if not size_data:
            break

        # Unpack the size of the modified frame data
        frame_size = struct.unpack("I", size_data)[0]

        # Receive the modified frame data from the server
        frame_data = b''
        while len(frame_data) < frame_size:
            data = webcamSocket.recv(frame_size - len(frame_data))
            if not data:
                break
            frame_data += data

        # Convert frame data to numpy array
        modified_frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

        # Display both original and modified frames
        should_continue = display_frames(frame, modified_frame)
        if not should_continue:
            break

    webcamSocket.close()
    cv2.destroyAllWindows()

def sendText():
    textSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    textServerAddress = ('127.0.0.1', 54321)
    textSocket.connect(textServerAddress)

    text = ""

    while text != "q":
        text = input("Enter text to send to server: ")

        # Send text to server
        textSocket.sendall(text.encode())

    textSocket.close()

def main():
    webcamThread = threading.Thread(target=sendAndReceiveFrames)
    textThread = threading.Thread(target=sendText)

    # Starting the threads
    textThread.start()
    webcamThread.start()

    # Waiting for both threads to finish
    webcamThread.join()
    textThread.join()

    print("All functions have finished executing")

if __name__ == "__main__":
    main()