import socket
import cv2
import struct
import numpy as np
import threading
from mobile_sam import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
import torch
import os
import json
from streamdiff import streamdiffusion, setprompt

textPrompt = "Normal"


# get the local address of the server
address = "0.0.0.0"


# MobileSAM initialization
model_type = "vit_t"
sam_checkpoint = "./MobileSAM/weights/mobile_sam.pt"

abspath = os.path.abspath(__file__) # sets directory of inference.py

device = "cuda" if torch.cuda.is_available() else "cpu"

mobile_sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
mobile_sam.to(device=device)
mobile_sam.eval()

stop = False

predictor = SamPredictor(mobile_sam)

annotation = []

def modify_frame(frame):
    global annotation
    # print("Annotation:", annotation)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # ndarray-ify
    predictor.set_image(frame)
    
    if len(annotation) > 0:
        masks, _, _ = predictor.predict(box=annotation)
    else:
        masks, _, _ = predictor.predict()
        
    # save mask
    # print(masks)
    # turn bool to int
    masks = masks.astype(np.uint8)
    # turn 0 and 1 to 0 and 255
    masks = masks * 255
    modified_frame = masks[0]
    return modified_frame

def send_receive_webcam_frames():
    webcamSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    webcamServerAddress = (address, 12345)
    webcamSocket.bind(webcamServerAddress)
    webcamSocket.listen(1)
    print("Server is listening...")
    connection, client_address = webcamSocket.accept()
    print("Client connected")

    while True:
        
        
        
        # Receive the size of the frame data from the client
        size_data = connection.recv(4)
        if not size_data:
            break

        # Unpack the size of the frame data
        frame_size = struct.unpack("I", size_data)[0]

        # Receive the frame data from the client
        frame_data = b''
        while len(frame_data) < frame_size:
            data = connection.recv(frame_size - len(frame_data))
            if not data:
                break
            frame_data += data
            
        start_time = cv2.getTickCount()

        # Convert frame data to numpy array
        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)


        sam_start = cv2.getTickCount()
        # Modify the frame
        modified_frame = modify_frame(frame)
        
        sam_end = cv2.getTickCount()
        sam_fps = cv2.getTickFrequency() / (sam_end - sam_start)
        print("SAM FPS:", sam_fps)
        
        diff_start = cv2.getTickCount()
        
        modified_frame = streamdiffusion(frame, modified_frame)
        
        diff_end = cv2.getTickCount()
        diff_fps = cv2.getTickFrequency() / (diff_end - diff_start)
        print("DIFF FPS:", diff_fps)
        
        # convert PIL image to cv2 image
        modified_frame = np.array(modified_frame)

        # Convert modified frame to JPEG format
        _, modified_frame_data = cv2.imencode('.jpg', modified_frame)

        # Get the size of the modified frame data
        modified_frame_size = len(modified_frame_data)

        # Pack the size of the modified frame data as a 4-byte integer
        modified_size_data = struct.pack("I", modified_frame_size)
        
        end_time = cv2.getTickCount()
        fps = cv2.getTickFrequency() / (end_time - start_time)
        print("FPS:", fps)

        # Send the size of the modified frame data to the client
        connection.sendall(modified_size_data)

        # Send the modified frame data to the client
        connection.sendall(modified_frame_data)
        
        
        

    connection.close()
    webcamSocket.close()

def receiveText():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (address, 54321)

    server_socket.bind(server_address)
    server_socket.listen(1)

    connection, client_address = server_socket.accept()

    global textPrompt
    global annotation
    tempData = ""
    text = ""
    annotations = []
    nextTempData = ""
    while text != "q":
        try:
            # Receive text from client
            tempData += connection.recv(1024*20).decode()
            
            
            newLineIndex = tempData.find("<end>")
            
            if newLineIndex == -1:
                continue
            else:
                tempData = tempData[:newLineIndex]
                nextTempData = tempData[newLineIndex+5:]
            
            # print("Received data from client:", tempData)
            
            newLineIndex = tempData.find("<split>")
            
            text = tempData[:newLineIndex]
            annotations = tempData[newLineIndex+7:]
            # print("Received text from client:", text)
            # print("Received annotations from client:", annotations)
            
            # json annotations
            
            floatArray = annotations.replace("[", "").replace("]", "").replace(" ", "").split(",")
            
            fake = False
            if len(floatArray) == 4:
                for i in range(len(floatArray)):
                    if floatArray[i] == "":
                        fake = True
                        break
                    floatArray[i] = float(floatArray[i])
                # print("ARRRR:",floatArray)
                if not fake:
                    annotation = np.array(floatArray)
            
            tempData = nextTempData
        except Exception as e:
            print("Error receiving data from client", e)
            break

    connection.close()
    server_socket.close()

def main():
    webcamThread = threading.Thread(target=send_receive_webcam_frames)
    textThread = threading.Thread(target=receiveText)

    webcamThread.daemon = True
    textThread.daemon = True

    # Starting the threads
    textThread.start()
    webcamThread.start()

    # Waiting for both threads to finish
    webcamThread.join()
    textThread.join()

    print("All functions have finished executing")

if __name__ == "__main__":
    main()