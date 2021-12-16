import namedmutex
import ctypes
from ctypes import sizeof, wintypes
import time
import mmap
import multiprocessing as mp
import multiprocessing.connection as mpc
import queue
import time
import socket
import tempfile
import os.path

import numpy as np
import cv2 as cv


# Function to run consumer process 1
def process1(proc_num, shared_buffer_shape, shared_latest_cam_buffer_idx,
             shared_buffers_idx_in_use, shared_gray_frames):
    '''shared_gray_frames
        proc_num: Process number (for the socket connection);
        shared_buffer_shape: size of the buffer (N x Height x Width)
        shared_latest_cam_buffer_idx: index of the last captured frame (in the
            shared_gray_frames)
        shared_buffers_idx_in_use: array with the number of processes using
            each stored frame.
        shared_gray_frames: actual buffer array that holds the captured frames;
    '''
    cv.namedWindow('Process 1')
    MAX_NUM_BYTES = 200
    # Connect to producer socket for this consumer
    f = open(r'\\.\pipe\pipe'+f'{proc_num}', 'rb', 0)

    # Get the shared mutex
    mutex = namedmutex.NamedMutex('ARMutex', existing=True, acquire=False)

    # Variable to hold the image processing result
    result_img = np.empty((shared_buffer_shape[0], shared_buffer_shape[1]),
                          dtype=np.uint8)
    start = time.time()
    num_frames = 0
    frame_idx = -1
    while True:
        # Wait for a signal that a new frame is available
        msg = f.read(MAX_NUM_BYTES)
        if msg.__len__() == 0:
            print("No bytes read!")
        elif msg.__len__() == MAX_NUM_BYTES:
            print("Not all bytes might have beed read!")

        # Check the index of the latest frame and signal its use
        mutex.acquire(4)
        if mutex.acquired:
            # Decrease the last frame index usage (except the first time)
            if frame_idx != -1:
                shared_buffers_idx_in_use[frame_idx] -= 1
            # Store the latest frame index
            frame_idx = shared_latest_cam_buffer_idx[0]
            # Increase the number of processes currently using this frame index
            shared_buffers_idx_in_use[frame_idx] += 1
        else:
            print('Unable to acquire mutex....')
            continue
        mutex.release()

        # Process frame
        # We do not need to use the shared_frame_arr lock, since the frame will
        # not be updated while we are using it.
        # This is just an example, you can do antyhing you want here
        cv.Canny(shared_gray_frames[frame_idx], 100, 50, edges=result_img)

        # Debug code: show the result and update the FPS indo
        cv.imshow('Process 1', result_img)
        cv.waitKey(5)
        num_frames += 1
        if num_frames == 100:
            end = time.time()
            print(f'Process 1: {num_frames/(end-start):.2f} FPS')
            num_frames = 0
            start = end


# Function to run consumer process 2
def process2(proc_num, shared_buffer_shape, shared_latest_cam_buffer_idx,
             shared_buffers_idx_in_use, shared_gray_frames):
    '''shared_gray_frames
        proc_num: Process number (for the socket connection);
        shared_buffer_shape: size of the buffer (N x Height x Width)
        shared_latest_cam_buffer_idx: index of the last captured frame (in the
            shared_gray_frames)
        shared_buffers_idx_in_use: array with the number of processes using
            each stored frame.
        shared_gray_frames: actual buffer array that holds the captured frames;
    '''
    cv.namedWindow('Process 2')
    MAX_NUM_BYTES = 200
    # Connect to producer socket for this consumer
    f = open(r'\\.\pipe\pipe'+f'{proc_num}', 'rb', 0)

    # Get the shared mutex
    mutex = namedmutex.NamedMutex('ARMutex', existing=True, acquire=False)

    # Variable to hold the image processing result
    result_img = np.empty((shared_buffer_shape[0], shared_buffer_shape[1]),
                          dtype=np.uint8)
    start = time.time()
    num_frames = 0
    frame_idx = -1
    while True:
        # Wait for a signal that a new frame is available
        msg = f.read(MAX_NUM_BYTES)
        if msg.__len__() == 0:
            print("No bytes read!")
        elif msg.__len__() == MAX_NUM_BYTES:
            print("Not all bytes might have beed read!")

        # Check the index of the latest frame and signal its use
        mutex.acquire(4)
        if mutex.acquired:
            # Decrease the last frame index usage (except the first time)
            if frame_idx != -1:
                shared_buffers_idx_in_use[frame_idx] -= 1
            # Store the latest frame index
            frame_idx = shared_latest_cam_buffer_idx[0]
            # Increase the number of processes currently using this frame index
            shared_buffers_idx_in_use[frame_idx] += 1
        else:
            print('Unable to acquire mutex....')
            continue
        mutex.release()

        # Process frame
        # We do not need to yse the shared_frame_arr lock, since the frame will
        # not be updated while we are using it.
        np.subtract(255, shared_gray_frames[frame_idx], out=result_img)

        # Debug code: show the result and update the FPS indo
        cv.imshow('Process 2', result_img)
        cv.waitKey(5)
        num_frames += 1
        if num_frames == 100:
            end = time.time()
            print(f'Process 2: {num_frames/(end-start):.2f} FPS')
            num_frames = 0
            start = end


# Producer process
if __name__ == '__main__':
    # Number of python processes accessing the camera images
    NUM_PYTHON_PROCESSES = 2  # The code below needs to be changed if this changes

    # Get access to the shared memory. We will do this in two runs, the first
    # to get the base sizes, and then the real deal.
    # Check the C# Producer code for more information on this
    shared_mem = mmap.mmap(fileno=-1, tagname='SharedMemory',
                           length=5*4, access=mmap.ACCESS_WRITE)

    offset = 0

    # shared_frame_height
    shared_frame_height = \
        np.frombuffer(buffer=shared_mem, dtype=np.int, count=1, offset=offset)
    frame_height = shared_frame_height[0]
    offset += 4
    
    # shared_frame_width
    shared_frame_width = \
        np.frombuffer(buffer=shared_mem, dtype=np.int, count=1, offset=offset)
    frame_width = shared_frame_width[0]
    offset += 4

    # shared_bgr_frame_step
    shared_bgr_frame_step = \
        np.frombuffer(buffer=shared_mem, dtype=np.int, count=1, offset=offset)
    bgr_frame_step = shared_bgr_frame_step[0]
    offset += 4

    # shared_gray_frame_step
    shared_gray_frame_step = \
        np.frombuffer(buffer=shared_mem, dtype=np.int, count=1, offset=offset)
    gray_frame_step = shared_gray_frame_step[0]
    offset += 4

    # Compute image sizes from the above data
    bgr_step_size =  frame_width*3
    bgr_frame_size = frame_height*bgr_step_size
    gray_step_size = frame_width
    gray_frame_size = frame_height*gray_step_size

    # shared_num_frame_buffers
    shared_num_frame_buffers = \
        np.frombuffer(buffer=shared_mem, dtype=np.uint8, count=1, offset=offset)
    num_frame_buffers = shared_num_frame_buffers[0]
    offset += 4

    # Reopen shared memory with the correct size
    shared_mem.close()
    shared_mem = mmap.mmap(
        fileno=-1, tagname='SharedMemory',
        length=5*4 + 1 + num_frame_buffers + bgr_frame_size + 
               num_frame_buffers*gray_frame_size,
        access=mmap.ACCESS_WRITE)

    # shared_latest_cam_buffer_idx
    shared_latest_cam_buffer_idx = \
        np.frombuffer(buffer=shared_mem, dtype=np.uint8, count=1, offset=offset)
    offset += 1

    # Local (non-shared) copy of the shared_latest_cam_buffer_idx
    latest_cam_buffer_idx = num_frame_buffers

    # shared_buffers_idx_in_use[NUM_FRAME_BUFFERS]
    shared_buffers_idx_in_use = np.frombuffer(
        buffer=shared_mem, dtype=np.uint8,
        count=num_frame_buffers, offset=offset
       )
    offset += num_frame_buffers

    # BGR image (not used here)
    shared_rgb_frame = np.frombuffer(
        buffer=shared_mem, dtype=np.uint8,
        count=bgr_frame_size, offset=offset
       ).reshape(frame_height, frame_width, 3)
    offset += bgr_frame_size
    
    # Grayscale images
    shared_gray_frames = list()
    for i in range(num_frame_buffers):
        shared_gray_frames.append(np.frombuffer(
            buffer=shared_mem, dtype=np.uint8,
            count=gray_frame_size,
            offset=offset,
           ).reshape(frame_height, frame_width))
        offset += gray_frame_size

    cv.namedWindow('Main process')

    # Create two processes
    proc1 = mp.Process(target=process1, name='Process1',
                       args=(1,
                             (frame_height, frame_width),
                             shared_latest_cam_buffer_idx,
                             shared_buffers_idx_in_use,
                             shared_gray_frames))
    proc2 = mp.Process(target=process2, name='Process2',
                       args=(2,
                             (frame_height, frame_width),
                             shared_latest_cam_buffer_idx,
                             shared_buffers_idx_in_use,
                             shared_gray_frames))

    # Start the two processes
    proc1.start()
    proc2.start()

    # Get the shared mutex
    mutex = namedmutex.NamedMutex('ARMutex', existing=True, acquire=False)

    # Wait until nboth processes are finished
    while True:
        mutex.acquire()
        cv.imshow('Main process', shared_rgb_frame)
        mutex.release()
        cv.waitKey(5)
        if (proc1.is_alive is False) and (proc2.is_alive is False):
            break
        #time.sleep(1.0)
