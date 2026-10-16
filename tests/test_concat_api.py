import socket,threading,json,unittest
from fusion.concat_bridge import ConcatClient

class ConcatTest(unittest.TestCase):
    def test_json_rpc_auth_version(self):
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);port=server.getsockname()[1]
        received=[]
        def routine():
            conn,_=server.accept()
            with conn:
                inp=conn.makefile('r',encoding='utf-8')
                for _ in range(2):
                    req=json.loads(inp.readline());received.append(req)
                    if req['method']=='auth':response={'jsonrpc':'2.0','id':0,'result':{}}
                    else:response={'jsonrpc':'2.0','id':req['id'],'result':{'apiVersion':'0.2','concat':'0.2.7'}}
                    conn.sendall((json.dumps(response)+'\n').encode())
        thread=threading.Thread(target=routine,daemon=True);thread.start()
        with ConcatClient(token='fake-local-test-token',port=port) as cli:
            result=cli.call('version')
            self.assertEqual(result['apiVersion'],'0.2')
        thread.join(timeout=3);server.close()
        self.assertEqual(received[0]['params']['token'],'fake-local-test-token')
        self.assertEqual(received[1]['method'],'version')
    def test_no_public_endpoint(self):
        with self.assertRaises(ValueError):ConcatClient(token='x',host='example.com')
if __name__=='__main__':unittest.main()
