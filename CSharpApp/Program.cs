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
        int frame_width = 640, frame_height = 480, num_channels = 3, fps = 30;
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

        String bgr_wname = "(C#) Color image"; //The name of the window
        String gray_wname = "(C#) Grayscale image"; //The name of the window
        CvInvoke.NamedWindow(bgr_wname); //Create the window using the specific name
        CvInvoke.NamedWindow(gray_wname); //Create the window using the specific name

        // Acquire first image
        Mat org_bgr_image = cam.QueryFrame();
        Mat org_gray_image = new Mat(frame_height, frame_width, DepthType.Cv8U, 1);
        CvInvoke.CvtColor(org_bgr_image, org_gray_image, ColorConversion.Bgr2Gray);

        // Create the named mutex. Only one system object named 
        // "MyMutex" can exist; the local Mutex object represents 
        // this system object, regardless of which process or thread
        // caused "MyMutex" to be created.
        Mutex m = new Mutex(false, "MyMutex");
        long bgr_img_size = org_bgr_image.Step * frame_height,
             gray_img_size = org_gray_image.Step * frame_height;
 
        // The shared memory will contain:
        //  -> BGR image
        //  -> Grayscale image
        using (MemoryMappedFile mmf = MemoryMappedFile.CreateNew("mySharedMem", bgr_img_size+gray_img_size))
        using (MemoryMappedViewAccessor accessor_view = mmf.CreateViewAccessor()) // Access entire shared memory
        {
            // Shared memory access pointer
            byte* acc_ptr = null;
            accessor_view.SafeMemoryMappedViewHandle.AcquirePointer(ref acc_ptr);

            // BGR image access
            Mat bgr_image = new Mat(frame_height, frame_width, DepthType.Cv8U,
                                    3, (IntPtr)acc_ptr,
                                    org_bgr_image.Step);

            // Grayscale image access
            Mat gray_image = new Mat(frame_height, frame_width, DepthType.Cv8U,
                                     1, (IntPtr)(acc_ptr + bgr_img_size), // Offset for the grayscale image
                                     org_gray_image.Step);
            
            // Main, infinite, cycle
            while (true)
            {
                // Try to gain control of the named mutex. If the mutex is 
                // controlled by another thread, wait for it to be released.        
                //Console.WriteLine("Waiting for the Mutex.");
                m.WaitOne();
                if (cam.Read(bgr_image) == false) Console.WriteLine("Unable to acquire frame...");
                CvInvoke.CvtColor(bgr_image, gray_image, ColorConversion.Bgr2Gray);
                m.ReleaseMutex();
                CvInvoke.Imshow(bgr_wname, bgr_image);
                CvInvoke.Imshow(gray_wname, gray_image);
                int key = CvInvoke.WaitKey(20);  //Wait for the key pressing event
                if (key == 'q')
                {
                    //Console.WriteLine("Exiting...");
                    break;
                }
                //Console.WriteLine("Mutex released.");
                //Thread.Sleep(2000);
            }
            accessor_view.SafeMemoryMappedViewHandle.ReleasePointer();
            mmf.Dispose();
        }

        CvInvoke.DestroyWindow(bgr_wname); //Destroy the window if key is pressed
        m.Dispose();
    }
}