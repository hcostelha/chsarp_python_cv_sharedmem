using System;
using System.IO;
using System.IO.Pipes;

namespace CSharpAppConsumer
{
    class Program
    {
        static void Main(string[] args)
        {
            int MAX_NUM_BYTES = 200;
            byte[] msg = new byte[MAX_NUM_BYTES];

            using (NamedPipeClientStream pipeClient =
            new NamedPipeClientStream(".", "pipe1", PipeDirection.In))
            {
                // Connect to the pipe or wait until the pipe is available.
                Console.Write("Attempting to connect to pipe...");
                pipeClient.Connect();
                Console.WriteLine("Connected to pipe.");

                int num_bytes_read = pipeClient.Read(msg, 0, MAX_NUM_BYTES);
                if (num_bytes_read == 0)
                    Console.WriteLine("No bytes read!");
                else if (num_bytes_read == MAX_NUM_BYTES)
                    Console.Write("Not all bytes might have beed read!");
                else
                {
                    Console.Write("Read: ");
                    for(int i = 0; i < num_bytes_read; i++ )
                        Console.Write(msg[i].ToString("D1"));
                    //Console.Write("Read: " + BitConverter.ToString(msg, 0, num_bytes_read));
                    // Console.Write((char[])msg, 0, num_bytes_read);
                }
            }
        }
    }
}
