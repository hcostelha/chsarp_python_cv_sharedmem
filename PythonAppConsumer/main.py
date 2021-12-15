import namedmutex
import ctypes
from ctypes import wintypes
import time
import mmap
import multiprocessing as mp
import multiprocessing.connection as mpc
import queue
import time

import numpy as np
import cv2 as cv


# Function to run consumer process 1
def process1(cons_queue, shared_frame_arr, shared_buffer_shape,
             shared_latest_cam_buffer_idx, shared_buffers_idx_in_use):
    '''
        cons_queue: This consumer queue. Willbe used to get a trigger for a new
            availabe frame;
        shared_frame_arr: actual buffer array that holds the captured frames;
        shared_buffer_shape: size of the buffer (N x Height x Width)
        shared_latest_cam_buffer_idx: index of the last captured frame (in the
            shared_frame_arr)
        shared_buffers_idx_in_use: array with the number of processes using
            each stored frame.
    '''
    cv.namedWindow('Process 1')
    frame_buffer = \
        np.frombuffer(shared_frame_arr.get_obj(), dtype='B'
                      ).reshape(shared_buffer_shape)
    result_img = np.empty((frame_buffer.shape[1], frame_buffer.shape[2]),
                          dtype=frame_buffer.dtype)
    start = time.time()
    num_frames = 0
    frame_idx = -1
    while True:
        # Wait for a signal that a new frame is available
        cons_queue.get(True, None)

        # Check the index of the latest frame and signal its use
        with shared_latest_cam_buffer_idx:
            # Decrease the last frame index usage (except the first time)
            if frame_idx != -1:
                shared_buffers_idx_in_use[frame_idx] -= 1
            # Store the latest frame index
            frame_idx = shared_latest_cam_buffer_idx.value
            # Increase the number of processes currently using this frame index
            shared_buffers_idx_in_use[frame_idx] += 1

        # Process frame
        # We do not need to use the shared_frame_arr lock, since the frame will
        # not be updated while we are using it.
        # This is just an example, you can do antyhing you want here
        cv.Canny(frame_buffer[frame_idx, :, :], 100, 50, edges=result_img)

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
def process2(cons_queue, shared_frame_arr, shared_buffer_shape,
             shared_latest_cam_buffer_idx, shared_buffers_idx_in_use):
    '''
        cons_queue: This consumer queue. Willbe used to get a trigger for a new
            availabe frame;
        shared_frame_arr: actual buffer array that holds the captured frames;
        shared_buffer_shape: size of the buffer (N x Height x Width)
        shared_latest_cam_buffer_idx: index of the last captured frame (in the
            shared_frame_arr)
        shared_buffers_idx_in_use: array with the number of processes using
            each stored frame.
    '''
    cv.namedWindow('Process 2')
    frame_buffer = \
        np.frombuffer(shared_frame_arr.get_obj(), dtype='B'
                      ).reshape(shared_buffer_shape)
    result_img = np.empty((frame_buffer.shape[1], frame_buffer.shape[2]),
                          dtype=frame_buffer.dtype)
    start = time.time()
    num_frames = 0
    frame_idx = -1
    while True:
        # Wait for a signal that a new frame is available
        cons_queue.get(True, None)

        # Check the index of the latest frame and signal its use
        with shared_latest_cam_buffer_idx:
            # Decrease the last frame index usage (except the first time)
            if frame_idx != -1:
                shared_buffers_idx_in_use[frame_idx] -= 1
            # Store the latest frame index
            frame_idx = shared_latest_cam_buffer_idx.value
            # Increase the number of processes currently using this frame index
            shared_buffers_idx_in_use[frame_idx] += 1

        # Process frame
        # We do not need to yse the shared_frame_arr lock, since the frame will
        # not be updated while we are using it.
        np.subtract(255, frame_buffer[frame_idx, :, :], out=result_img)

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

    f = open('\\\\.\\pipe\\pipe1', 'r+b', 0)
    ola = f.readall()

    f =  mpc.Client(r'\.\pipe{PipeName}', 'AF_PIPE', authkey=None)

    f =  mpc.Client('\\\\.\\pipe\\pipe1', 'AF_PIPE', authkey=None)



    # Number processes accessing the camera images
    NUM_PROCESSES = 2
    NUM_FRAME_BUFFERS = NUM_PROCESSES + 2
    frame_height = 480
    frame_width = 640
    num_channels = 3
    bgr_step_size =  frame_width*num_channels
    gray_step_size = frame_width
    fps = 30

    # Access shared memory
    # BGR image
    rgbmap = mmap.mmap(fileno=-1, tagname='mySharedMem',
                      length=frame_height*bgr_step_size + frame_height*gray_step_size,
                      access=mmap.ACCESS_READ)
    rgb_frame = np.frombuffer(buffer=rgbmap, dtype=np.uint8,
                              count=frame_height*bgr_step_size, offset=0
                             ).reshape(frame_height, frame_width, num_channels)
    
    # Grayscale image
    gray_frame = np.frombuffer(buffer=rgbmap, dtype=np.uint8,
                               count=frame_height*gray_step_size,
                               offset=frame_height*bgr_step_size
                              ).reshape((frame_height, frame_width))

    # Get the shared mutex
    mutex = namedmutex.NamedMutex('MyMutex', existing=True, acquire=False)

    cv.namedWindow('Main process')
    print(f'Expected FPS: {fps}')

    # Create the shared array for the camera image
    shared_buffer_shape = (
        NUM_PROCESSES+2, gray_frame.shape[0], gray_frame.shape[1])
    # The first argument, 'B', specifies 'unsigned char' (8 bits). See
    # https://docs.python.org/3/library/array.html#module-array
    shared_frame_arr = mp.Array('B', int(np.prod(shared_buffer_shape)),
                                lock=mp.Lock())
    # Create a numpy array without allocating new memory, it will use the
    # shared array memory, so as to be shareable between different processes.
    gray_frame_buffer = np.frombuffer(shared_frame_arr.get_obj(), dtype='B'
                                      ).reshape(shared_buffer_shape)

    # Create the shared variable for the latest camera frame index
    shared_latest_cam_buffer_idx = mp.Value('b', -1)

    # Create the shared array to hold the number of processes using each frame
    shared_buffers_idx_in_use = mp.Array('B', NUM_FRAME_BUFFERS)
    shared_buffers_idx_in_use_array = np.frombuffer(
        shared_buffers_idx_in_use.get_obj(), dtype='B')

    # Create a queue for each process. No need to have more than 2 elements.
    cons_queues = [mp.Queue(2) for i in range(NUM_PROCESSES)]

    # Create two processes
    proc1 = mp.Process(target=process1, name='Process1',
                       args=(cons_queues[0],
                             shared_frame_arr,
                             shared_buffer_shape,
                             shared_latest_cam_buffer_idx,
                             shared_buffers_idx_in_use))
    proc2 = mp.Process(target=process2, name='Process2',
                       args=(cons_queues[1],
                             shared_frame_arr,
                             shared_buffer_shape,
                             shared_latest_cam_buffer_idx,
                             shared_buffers_idx_in_use))

    # Start the two processes
    proc1.start()
    proc2.start()

    # Acquire and process each frame until the ESC key is pressed.
    start = time.time()
    num_frames = 0
    while True:
        # Find free (unused) frame buffer
        next_cam_buffer_idx = -1
        with shared_latest_cam_buffer_idx:
            for i in range(NUM_FRAME_BUFFERS):
                if (shared_buffers_idx_in_use_array[i] == 0) and \
                   (i != shared_latest_cam_buffer_idx.value):
                    next_cam_buffer_idx = i
                    break
        # Safety check
        if next_cam_buffer_idx == -1:
            raise RuntimeError('No available buffer index!')

        # Access the image in the shared memory.
        mutex.acquire(4)
        if mutex.acquired:
            np.copyto(dst=gray_frame_buffer[next_cam_buffer_idx, :, :],
                      src=gray_frame)
            #cv.cvtColor(src=rgb_frame, code=cv.COLOR_BGR2GRAY,
            #            dst=gray_frame_buffer[next_cam_buffer_idx, :, :])
            cv.imshow('Main process (BGR)', rgb_frame)
            cv.imshow('Main process (GRAY)', gray_frame)
            mutex.release()
        else:
            print('Unable to acquire mutex....')
            continue
            
        # Updated the latest frame buffer index
        with shared_latest_cam_buffer_idx:
            shared_latest_cam_buffer_idx.value = next_cam_buffer_idx

        # Signal consumers that a new image is available
        for i in range(NUM_PROCESSES):
            try:
                cons_queues[i].put(True, block=False)
            except queue.Full:
                pass

        # Debug code: show the last frame and update the FPS info
        cv.imshow('Main process',
                  gray_frame_buffer[shared_latest_cam_buffer_idx.value, :, :])
        if cv.waitKey(5) == 27:
            break
        num_frames += 1
        if num_frames == 100:
            end = time.time()
            print(f'Process 0: {num_frames/(end-start):.2f} FPS')
            num_frames = 0
            start = end
