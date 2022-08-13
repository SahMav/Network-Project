import struct
print('b' + '192.128.001.001')
s = "127.000.000.001"
parts = s.split(".")
print(parts)
print(s.encode('utf-8'))
port = '31315'
t = 'REQ'
n = '6'
to_pack = [1, 5, 4, int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(port),t.encode('utf-8'), n.encode('utf-8')]
format = '>HHIHHHHI3s1s'
# for node in nodes_array:
#     to_pack.append(node.server_ip)
#     to_pack.append(node.server_port)
#     format += '15s'
#     format += '5s'
to_unpack = b'\x00\x01\x00\x05\x00\x00\x00\x04\x00\x7f\x00\x00\x00\x00\x00\x01\x00\x00zSREQ6'
result = struct.unpack(format, to_unpack)
print(result)

var = struct.pack(format, *to_pack)
print(var)