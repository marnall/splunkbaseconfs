import java.sql.*;

public class JDBCConnect {
    public static void main(String args[]) {
        String DB_URL = args[0];
        String USER = args[1];
        String PASS = args[2];
        Connection conn = null;
        try{
            //Open a connection
            conn = DriverManager.getConnection(DB_URL,USER,PASS);
            conn.close();
        }catch(SQLException se){
            System.out.println(se);
        }catch(Exception e){
            //Handle errors for Class.forName
            System.out.println(e);
        }finally{
            try{
            if(conn!=null)
                conn.close();
            }catch(SQLException se){
            se.printStackTrace();
            }
        }
    }
}
