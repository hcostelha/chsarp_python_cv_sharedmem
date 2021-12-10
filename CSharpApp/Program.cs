using System;
using System.Threading;
using System.IO;
using System.IO.MemoryMappedFiles;

using Emgu.CV;
using Emgu.CV.CvEnum;
using Emgu.CV.Structure;
using System.Runtime.CompilerServices;

public class MultiProcessShMemWithPython
{
    public static unsafe void Main()
    {
        int frame_width = 640, frame_height = 480, fps = 30;
        // For EMGU docs, see https://www.emgu.com/wiki/files/4.5.4/document/html/R_Project_Emgu_CV_Documentation.htm
        VideoCapture cam = new VideoCapture(0, VideoCapture.API.Any);
        // set video properties
        // More properties at: https://www.emgu.com/wiki/files/4.5.4/document/html/T_Emgu_CV_CvEnum_CapProp.htm
        // Frames per second
        if (cam.Set(CapProp.Fps, fps) == false) Console.WriteLine("Unable to change FPS");
        // Width
        if (cam.Set(CapProp.FrameWidth, frame_width) == false) Console.WriteLine("Unable to change frame width");
        // Frames per second
        if (cam.Set(CapProp.FrameHeight, frame_height) == false) Console.WriteLine("Unable to change frame height");

        String wname = "Test Window"; //The name of the window
        CvInvoke.NamedWindow(wname); //Create the window using the specific name

        // Acquire first image
        Mat org_image = cam.QueryFrame();

        // Create the named mutex. Only one system object named 
        // "MyMutex" can exist; the local Mutex object represents 
        // this system object, regardless of which process or thread
        // caused "MyMutex" to be created.
        Mutex m = new Mutex(false, "MyMutex");
        int imgsz = frame_width * frame_height * 3;  // 3 channel - BGR
 
        int key = -1;
        int var = 0;
        // I have not found an easy way to determine the amount of memory being
        // used by an image, so I am simply using the double of the needed data.
        using (MemoryMappedFile mmf = MemoryMappedFile.CreateNew("mySharedMem", 2* imgsz))
        {
            using (MemoryMappedViewAccessor accessor_view = mmf.CreateViewAccessor())
            {
                byte* acc_ptr = null;
                accessor_view.SafeMemoryMappedViewHandle.AcquirePointer(ref acc_ptr);

                //Mat image = new Mat(frame_height, frame_width, DepthType.Cv8U, 3);
                Mat image = new Mat(frame_height, frame_width, DepthType.Cv8U, 3, (IntPtr)acc_ptr, org_image.Step);

                // var = (var+1)%10;
                // accessor_view.Write(0, var);
                while (true)  // Main, infinite, cycle
                {
                    // Try to gain control of the named mutex. If the mutex is 
                    // controlled by another thread, wait for it to be released.        
                    Console.WriteLine("Waiting for the Mutex.");
                    m.WaitOne();

                    // Keep control of the mutex until the user presses 'q'
                    Console.WriteLine("This application owns the mutex. " +
                        "Press q to release the mutex and exit.");
                    if(Console.KeyAvailable)
                    {
                        if(Console.ReadKey().KeyChar == 'q')
                        {
                            Console.WriteLine("Exiting...");
                            break;
                        }
                    }
                    //image = cam.QueryFrame();
                    if (cam.Read(image) == false) Console.WriteLine("Unable to acquire frame...");
                    CvInvoke.Imshow(wname, image);
                    key = CvInvoke.WaitKey(5);  //Wait for the key pressing event
                    if(key == 'q')
                    {
                        Console.WriteLine("Exiting...");
                        break;
                    }
                    m.ReleaseMutex();
                    Console.WriteLine("Mutex released.");
                    //Thread.Sleep(2000);
                }
                accessor_view.SafeMemoryMappedViewHandle.ReleasePointer();
            }
        }

        CvInvoke.DestroyWindow(wname); //Destroy the window if key is pressed
        m.ReleaseMutex();
    }
}