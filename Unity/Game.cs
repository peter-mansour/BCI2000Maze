using System.Collections;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.IO;
using UnityEngine;
using System.Net.Sockets;
using System.Threading;
using System.Text;

public class Game : MonoBehaviour
{
    private string IPAddress = "192.168.1.8";
    private int PORT = 9001;
    private string msg = "{ \"request\": \"_x_watch_x_\", \"plyr_ip\": \"\", \"plyr_clr\": \"\", \"direction\": \"\", \"degree\": 0}";
    private List<string> msgs;

    void Start(){
        Client.Init(IPAddress, PORT);
        Client.Send(msg);
    }

    void Update(){
        msgs = Client.get_msgs();
        foreach (string m in msgs){
            Pkt pkt_content = JsonUtility.FromJson<Pkt>(m);
            Debug.Log(pkt_content.direction);
        }
        //do stuff
    }
}

public class Client
{
    private static int BUFF_SZ = 10000;
    private static Thread listen_th;
    private static TcpClient sckt;
    private static byte[] inbuff;
    private static NetworkStream pipe;
    private static string delim = "?_?";
    public static Queue<string> outbuff = new Queue<string>();

    public static void Init(string ip, int port){
        sckt = new TcpClient(ip, port);
        listen_th = new Thread(new ThreadStart(Rcv));
        inbuff = new byte[BUFF_SZ];
        pipe = sckt.GetStream();
        Connect();
    }

    private static void Connect(){
        try{
            listen_th.IsBackground = true;
            listen_th.Start();
        }
        catch (System.Exception e){
            Debug.Log(e);
        }
    }

    private static void Rcv(){
        try{
            while (true){
                using (pipe){
                    while (pipe.Read(inbuff, 0, inbuff.Length) > 0){
                        string[] msgs = Encoding.Default.GetString(inbuff).Split(
                            new string[] { delim }, System.StringSplitOptions.None);
                        for (uint i = 0; i < msgs.Length; i++){
                            lock (outbuff){
                                outbuff.Enqueue(msgs[i]);
                            }
                        }
                    }
                }
            }
        }
        catch (SocketException e){
            Debug.Log(e);
        }
    }

    // wrap buffer locking
    public static List<string> get_msgs() {
        List<string> msgs = new List<string>();
        while (outbuff.Count != 0) {
            lock (outbuff){
                msgs.Add(outbuff.Dequeue());
            }
        }
        return msgs;
    }

    public static void Send(string msg){
        if (sckt != null){
            try{
                if (pipe.CanWrite){
                    byte[] msg_bytes = Encoding.ASCII.GetBytes(msg);
                    pipe.Write(msg_bytes, 0, msg_bytes.Length);
                }
            }
            catch (SocketException e){
                Debug.Log(e);
            }
        }
    }
}

class Pkt
{
    public string request = string.Empty;
    public string plyr_ip = string.Empty;
    public string plyr_clr = string.Empty;
    public string direction = string.Empty;
    public int degree = -1;
}