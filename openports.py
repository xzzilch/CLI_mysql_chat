import socket

#_______________________________________________________________________
def localip():
    '''Gets local ip'''
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect or send data to this IP
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    return local_ip
#print(localip())


#_______________________________________________________________________
def portstatus(port, timeout=1.0, ip=None):
    '''Checks status of a port for a ip'''
    
    if ip is None:
        ip = localip()
        
    # a TCP socket
    # AF_INET = IPv4, SOCK_STREAM = TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        # connect_ex returns 0 if the connection was successful
        result = s.connect_ex((ip, port))
        if result == 0:
            s.close()
            return True, f"{port} : OPEN"
        else:
            return False, f"{port} : CLOSED"
            
    except Exception as e:
        print(f"Error checking {ip}:{port} -> {e}")
        return False, f"{port} : ERROR"
        
    finally:
        try:
            s.close()
        except Exception:
            pass
#print(portstatus(80))
