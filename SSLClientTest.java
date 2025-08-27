import javax.net.ssl.SSLContext;
import javax.net.ssl.KeyManagerFactory;
import java.security.KeyStore;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLParameters;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.net.URL;
import java.net.Socket;
import java.net.SocketException;
import java.security.KeyStore;
import java.io.FileInputStream;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.util.regex.Pattern;

public class SSLClientTest {
  /* Just connect to Tomcat using jsse */
  protected URL url;
  private Socket socket;
  protected void setSocket(Socket socket) throws SocketException {
	this.socket = socket;
	socket.setSoTimeout(60000);
  }
  protected void setURL(URL url) {
    this.url = url;
  }
  private static final TrustManager[] trustAllCerts = new TrustManager[]{
        new X509TrustManager() {

            @Override
            public java.security.cert.X509Certificate[] getAcceptedIssuers() {
                return null;
            }

            @Override
            public void checkClientTrusted(java.security.cert.X509Certificate[] certs, String authType) {
            }

            @Override
            public void checkServerTrusted(java.security.cert.X509Certificate[] certs, String authType) {
            }
        }
  };

  private void sendHeader(OutputStream os) throws Exception {
		String httpQuery = "GET " + this.url.getPath() + " HTTP/1.1\r\n" 
				+ "User-Agent: " + SSLClientTest.class.getName() + "\r\n" 
				+ "Host: " + this.url.getHost() + "\r\n" + "\r\n";
		os.write(httpQuery.getBytes());
		os.flush();
	}
  private String List(String[] strings) {
    String s = "";
    for (int i=0; i< strings.length; i++) {
      if (i !=0)
        s = s + " ";
      s = s + strings[i];
    }
    return s;
  }

  public void connect() throws Exception {
        try {
            SSLContext sslCtx = SSLContext.getInstance("TLS");
            KeyManagerFactory kmf = KeyManagerFactory.getInstance("SunX509");
            KeyStore ks = KeyStore.getInstance("JKS");
            String fileName = "ks";
            char[] passphrase = "changeit".toCharArray();
            ks.load(new FileInputStream(fileName), passphrase);
            kmf.init(ks, passphrase);
            sslCtx.init(kmf.getKeyManagers(), trustAllCerts, new java.security.SecureRandom());
            SSLSocketFactory socketFactory = sslCtx.getSocketFactory();
            // Open connection with server
            SSLSocket socket = (SSLSocket) socketFactory.createSocket(this.url.getHost(), this.url.getPort());
            setSocket(socket);
            SSLParameters params = socket.getSSLParameters();
            System.out.println("Protocols: " + List(params.getProtocols()));
            System.out.println("CipherSuites: " + List(params.getCipherSuites()));
            System.out.println("NamedGroups: " + List(params.getNamedGroups()));
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }
    public void runit() throws Exception {
      OutputStream os = this.socket.getOutputStream();
      sendHeader(os);
      BufferedReader in = new BufferedReader(new InputStreamReader(this.socket.getInputStream()));
      String line = null;
      Pattern pattern = Pattern.compile("\\s*");
      while ((line = in.readLine()) != null && !pattern.matcher(line).matches()) {
			System.out.println(line);
		}
    }
    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: java " + SSLClientTest.class.getName()
                    + " URL");
            System.err.println("\tURL: The url of the service to test.");
            System.exit(1);
        }

        URL strURL = new URL(args[0]);
        SSLClientTest test = new SSLClientTest();
        test.setURL(strURL);
        test.connect();
        System.out.println("Connected");
        test.runit();
        System.out.println("Done");
   }
}
