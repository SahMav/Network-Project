from Stream import Stream
from tools.Node import Node
from Packet import Packet, PacketFactory
from UserInterface import UserInterface
from tools.SemiNode import SemiNode
from tools.NetworkGraph import NetworkGraph, GraphNode
import time
import threading

ENDTIME = 36
ROOTTIME = 20

"""
    Peer is our main object in this project.
    In this network Peers will connect together to make a tree graph.
    This network is not completely decentralised but will show you some real-world challenges in Peer to Peer networks.

"""


class Peer:
    def __init__(self, server_ip, server_port, is_root=False, root_address=None):
        """
        The Peer object constructor.

        Code design suggestions:
            1. Initialise a Stream object for our Peer.
            2. Initialise a PacketFactory object.
            3. Initialise our UserInterface for interaction with user commandline.
            4. Initialise a Thread for handling reunion daemon.

        Warnings:
            1. For root Peer, we need a NetworkGraph object.
            2. In root Peer, start reunion daemon as soon as possible.
            3. In client Peer, we need to connect to the root of the network, Don't forget to set this connection
               as a register_connection.


        :param server_ip: Server IP address for this Peer that should be pass to Stream.
        :param server_port: Server Port address for this Peer that should be pass to Stream.
        :param is_root: Specify that is this Peer root or not.
        :param root_address: Root IP/Port address if we are a client.

        :type server_ip: str
        :type server_port: int
        :type is_root: bool
        :type root_address: tuple
        """
        self.is_root = is_root
        server_port = Node.parse_port(server_port)
        server_ip = Node.parse_ip(server_ip)
        self.server_ip = server_ip
        self.server_port = server_port
        self.stream = Stream(server_ip, server_port)
        self.packet_factory = PacketFactory()
        self.user_interface = UserInterface()
        self.t_reunion = threading.Thread(target=self.run_reunion_daemon)
        self.t_reunion.daemon = True
        self.t_run = threading.Thread(target=self.run)
        self.t_run.daemon = True
        if self.is_root == True:
            self.registered_peers = []
            root_node = GraphNode((server_ip, server_port))
            self.network_graph = NetworkGraph(root_node)
            self.is_registered = True
            self.t_reunion.start()
        else:
            self.hello_back_received_time = -2
            self.hello_sent_time = -2
            self.parents_address = None
            self.is_registered = False
            self.stream.add_node(root_address, True)
            root_ip = Node.parse_ip(root_address[0])
            root_port = Node.parse_port(root_address[1])
            self.root_address = (root_ip, root_port)
            register_packet = PacketFactory.new_register_packet('REQ', (server_ip, server_port), (server_ip, server_port))
            # print ("init: reg req pack: ", register_packet)
            print("Register Packet sent from ", (self.server_ip, self.server_port), "    to    ", self.root_address)
            print(register_packet.get_buf(), '\n\n')
            self.stream.add_message_to_out_buff(root_address, register_packet.get_buf())
        # self.start_user_interface()
        # self.user_interface.start()
        print('finished initializing peer')


        return

    def start_user_interface(self):
        """
        For starting UserInterface thread.

        :return:
        """
        # FIXME
        # t_ui = threading.Thread(target=self.user_interface.run)
        # t_ui.daemon = True
        # t_ui.start()
        # self.user_interface.start()
        self.user_interface.run()
        return
        return

    def handle_user_interface_buffer(self):
        """
        In every interval, we should parse user command that buffered from our UserInterface.
        All of the valid commands are listed below:
            1. Register:  With this command, the client send a Register Request packet to the root of the network.
            2. Advertise: Send an Advertise Request to the root of the network for finding first hope.
            3. SendMessage: The following string will be added to a new Message packet and broadcast through the network.

        Warnings:
            1. Ignore irregular commands from the user.
            2. Don't forget to clear our UserInterface buffer.
        :return:
        """
        buffer = self.user_interface.buffer
        if len(buffer) == 0:
            return
        if len(buffer) == 1:
            buffer = buffer[0].split(' ')
        print ("peer, handle user interface: ", buffer)
        if buffer[0] == 'Register':
            if self.is_root:
                print ('You are a root user. You can not register!')
            else:
                register_node = self.stream.get_node_by_server(self.root_address[0], self.root_address[1])
                if register_node == None:
                    register_node = self.stream.add_node(self.root_address, True)
                register_packet = PacketFactory.new_register_packet('REQ', (self.server_ip, self.server_port), (self.server_ip, self.server_port))
                # print ("reg req pack: ", register_packet.get_body())
                print("Register Packet sent from ", (self.server_ip, self.server_port), "    to    ", self.root_address)
                print(register_packet.get_buf(), '\n\n')
                self.stream.add_message_to_out_buff(self.root_address, register_packet.get_buf())

        elif buffer[0] == 'Advertise':
            if self.is_root:
                print ('You are a root user. You can not advertise!')
            else:
                advertise_node = self.stream.get_node_by_server(self.root_address[0], self.root_address[1])
                if advertise_node == None:
                    advertise_node = self.stream.add_node(self.root_address, True)
                advertise_packet = PacketFactory.new_advertise_packet('REQ', (self.server_ip, self.server_port))
                # print ("handle_ui: adv req pack: ", advertise_packet.get_body())
                print("Advertise Packet sent from ", (self.server_ip, self.server_port), "    to    ", self.root_address)
                print(advertise_packet.get_buf(), '\n\n')
                self.stream.add_message_to_out_buff(self.root_address, advertise_packet.get_buf())

        elif buffer[0] == 'SendMessage':
            print ("Sending message: ", buffer[1])
            message_packet = PacketFactory.new_message_packet(buffer[1], (self.server_ip, self.server_port))
            # print ("msg pack: ", message_packet.get_body())
            self.send_broadcast_packet(message_packet)
        self.user_interface.buffer = []
        return

    def run(self):
        """
        The main loop of the program.

        Code design suggestions:
            1. Parse server in_buf of the stream.
            2. Handle all packets were received from our Stream server.
            3. Parse user_interface_buffer to make message packets.
            4. Send packets stored in nodes buffer of our Stream object.
            5. ** sleep the current thread for 2 seconds **

        Warnings:
            1. At first check reunion daemon condition; Maybe we have a problem in this time
               and so we should hold any actions until Reunion acceptance.
            2. In every situation checkout Advertise Response packets; even is Reunion in failure mode or not

        :return:
        """
        while(True):
            # print(" =====================running=========================")
            # TODO: Implement and check warnings
            for msg in self.stream.read_in_buf():
                input_packet = PacketFactory.parse_buffer(msg)
                self.handle_packet(input_packet)
            self.stream.clear_in_buff()
            self.handle_user_interface_buffer()
            self.stream.send_out_buf_messages()
            time.sleep(2)
        pass

    def remove_peer(self, address):
        reg_node = self.stream.get_node_by_server(address[0], address[1])
        self.stream.remove_node(reg_node)
        self.network_graph.remove_node(address)

    def run_reunion_daemon(self):
        """

        In this function, we will handle all Reunion actions.

        Code design suggestions:
            1. Check if we are the network root or not; The actions are identical.
            2. If it's the root Peer, in every interval check the latest Reunion packet arrival time from every node;
               If time is over for the node turn it off (Maybe you need to remove it from our NetworkGraph).
            3. If it's a non-root peer split the actions by considering whether we are waiting for Reunion Hello Back
               Packet or it's the time to send new Reunion Hello packet.

        Warnings:
            1. If we are the root of the network in the situation that we want to turn a node off, make sure that you will not
               advertise the nodes sub-tree in our GraphNode.
            2. If we are a non-root Peer, save the time when you have sent your last Reunion Hello packet; You need this
               time for checking whether the Reunion was failed or not.
            3. For choosing time intervals you should wait until Reunion Hello or Reunion Hello Back arrival,
               pay attention that our NetworkGraph depth will not be bigger than 8. (Do not forget main loop sleep time)
            4. Suppose that you are a non-root Peer and Reunion was failed, In this time you should make a new Advertise
               Request packet and send it through your register_connection to the root; Don't forget to send this packet
               here, because in the Reunion Failure mode our main loop will not work properly and everything will be got stock!

        :return:
        """
        while(True):
            if self.is_root:
                for node in self.network_graph.nodes:
                    if ((time.time() - node.reunion_time) > ROOTTIME) and node != self.network_graph.root \
                     and node.reunion_time != -1:
                        # Remove node from stream and graph
                        print("\nRemoveing node   ", node.address, "\n")
                        self.remove_peer(node.address)
            else:
                if self.parents_address == None:
                    print("this is root!")
                    continue
                if (self.hello_sent_time <= -1) or ((time.time() - self.hello_sent_time) < ENDTIME) \
                 and (self.hello_back_received_time - self.hello_sent_time > 0):
                    # Send packet
                    # print("first if, send packet")
                    reunion_node = self.stream.get_node_by_server(self.parents_address[0], self.parents_address[1])
                    if reunion_node == None:
                        print ("Must not happen: Parents node not found! Error!")
                    reunion_packet = PacketFactory.new_reunion_packet('REQ', (self.server_ip, self.server_port), [(self.server_ip, self.server_port)])
                    print("Reunion packet sent from   ", (self.server_ip, self.server_port),"  to   ", self.parents_address)
                    print(reunion_packet.get_buf(), '\n\n')
                    self.stream.add_message_to_out_buff(self.parents_address, reunion_packet.get_buf())
                    self.hello_sent_time = time.time()
                elif ((time.time() - self.hello_sent_time) > ENDTIME):
                    # We have a problem
                    print("Endtime has exceeded. Sending advertisement again")
                    self.hello_sent_time = -1
                    advertise_node = self.stream.get_node_by_server(self.root_address[0], self.root_address[1])
                    if advertise_node == None:
                        advertise_node = self.stream.add_node(self.root_address, True)
                    advertise_packet = PacketFactory.new_advertise_packet('REQ', (self.server_ip, self.server_port))
                    # print ("adv req pack: ", advertise_packet.get_body())
                    print("Advertisement packet sent from   ", (self.server_ip, self.server_port), "  to   ",
                          self.root_address)
                    print(advertise_packet.get_buf(), '\n\n')
                    self.stream.add_message_to_out_buff(self.root_address, advertise_packet.get_buf())

            print("\n", "----------------------sleepy time-----------------------", "\n")
            time.sleep(6)
        return

    def send_broadcast_packet(self, broadcast_packet):
        """

        For setting broadcast packets buffer into Nodes out_buff.

        Warnings:
            1. Don't send Message packets through register_connections.

        :param broadcast_packet: The packet that should be broadcast through the network.
        :type broadcast_packet: Packet

        :return:
        """
        for node in self.stream.nodes:
            if node.set_register == True:
                continue
            self.stream.add_message_to_out_buff(node.get_server_address(), broadcast_packet.get_buf())
        return

    def handle_packet(self, packet):
        """

        This function act as a wrapper for other handle_###_packet methods to handle the packet.

        Code design suggestion:
            1. It's better to check packet validation right now; For example Validation of the packet length.

        :param packet: The arrived packet that should be handled.

        :type packet Packet

        """

        if packet.type == 1 and (packet.length == 23 or packet.length == 6):
            self.__handle_register_packet(packet)
        elif packet.type == 2 and (packet.length == 23 or packet.length == 3):
            self.__handle_advertise_packet(packet)
        elif packet.type == 3 and packet.length == 4:
            self.__handle_join_packet(packet)
        elif packet.type == 4:
            self.__handle_message_packet(packet)
        elif packet.type == 5:
            self.__handle_reunion_packet(packet)
        pass

    def __check_registered(self, source_address):
        """
        If the Peer is the root of the network we need to find that is a node registered or not.

        :param source_address: Unknown IP/Port address.
        :type source_address: tuple

        :return:
        """
        return (source_address in self.registered_peers)

    def __handle_advertise_packet(self, packet):
        """
        For advertising peers in the network, It is peer discovery message.

        Request:
            We should act as the root of the network and reply with a neighbour address in a new Advertise Response packet.

        Response:
            When an Advertise Response packet type arrived we should update our parent peer and send a Join packet to the
            new parent.

        Code design suggestion:
            1. Start the Reunion daemon thread when the first Advertise Response packet received.
            2. When an Advertise Response message arrived, make a new Join packet immediately for the advertised address.

        Warnings:
            1. Don't forget to ignore Advertise Request packets when you are a non-root peer.
            2. The addresses which still haven't registered to the network can not request any peer discovery message.
            3. Maybe it's not the first time that the source of the packet sends Advertise Request message. This will happen
               in rare situations like Reunion Failure. Pay attention, don't advertise the address to the packet sender
               sub-tree.
            4. When an Advertise Response packet arrived update our Peer parent for sending Reunion Packets.

        :param packet: Arrived register packet

        :type packet Packet

        :return:
        """
        if self.is_root and packet.get_body()[2] == 'Q':
            senders_address = packet.get_source_server_address()
            print("Advertise Packet received from ", packet.get_source_server_address())
            print(packet.get_buf(), '\n\n')
            if self.__check_registered(senders_address):
                advertise_node = self.stream.get_node_by_server(senders_address[0], senders_address[1])
                if advertise_node == None:
                    advertise_node = self.stream.add_node(senders_address)
                parents_address = self.__get_neighbour(senders_address)
                advertise_packet = PacketFactory.new_advertise_packet('RES', (self.server_ip, self.server_port), parents_address)
                # print ("adv res pack: ", advertise_packet.get_body())
                print("Advertise response Packet sent from ", (self.server_ip, self.server_port), "    to    ", packet.get_source_server_address())
                print(advertise_packet.get_buf(), '\n\n')
                self.stream.add_message_to_out_buff(senders_address, advertise_packet.get_buf())
            else:
                print ("You are not registered yet. You can not send advertise message!")
                return
        elif self.is_root == False and packet.get_body()[2] == 'S':
            print("Advertise response Packet received from ", packet.get_source_server_address())
            print(packet.get_buf(), '\n\n')
            self.parents_address = (packet.get_body()[3:18], packet.get_body()[18:23])
            parents_node = self.stream.get_node_by_server(self.parents_address[0], self.parents_address[1])
            if parents_node == None or parents_node.set_register:
                parents_node = self.stream.add_node(self.parents_address, False)
            join_packet = PacketFactory.new_join_packet((self.server_ip, self.server_port))
            # print ("join req pack: ", join_packet.get_body())
            print("Join Packet sent from ", (self.server_ip, self.server_port), "   to  ", self.parents_address)
            print(join_packet.get_buf(), '\n\n')
            self.stream.add_message_to_out_buff(self.parents_address, join_packet.get_buf())
            print("Start reunion daemon for peer : ", (self.server_ip, self.server_port))
            if self.hello_sent_time == -2:
                self.t_reunion.start()
        return

    def __handle_register_packet(self, packet):
        """
        For registration a new node to the network at first we should make a Node with stream.add_node for'sender' and
        save it.

        Code design suggestion:
            1.For checking whether an address is registered since now or not you can use SemiNode object except Node.

        Warnings:
            1. Don't forget to ignore Register Request packets when you are a non-root peer.

        :param packet: Arrived register packet
        :type packet Packet
        :return:
        """
        if self.is_root and packet.get_body()[2] == 'Q':
            senders_address = packet.get_source_server_address()
            print("Register Packet received from ", packet.get_source_server_address())
            print(packet.get_buf(), '\n\n')
            if not (self.__check_registered(senders_address)):
                # print ("REQUEST HANDLE REGISTER ", senders_address)
                self.stream.add_node(senders_address, True)
                register_packet = PacketFactory.new_register_packet('RES', senders_address)
                # print ("reg res pack: ", register_packet)
                print("Register response Packet sent from ", (self.server_ip, self.server_port), "    to    ",
                      packet.get_source_server_address())
                print(register_packet.get_buf(), '\n\n')

                self.stream.add_message_to_out_buff(senders_address, register_packet.get_buf())
                self.registered_peers.append(senders_address)
            else:
                print("Peer already registered!")
        elif self.is_root == False and packet.get_body()[2] == 'S':
            print ("Peer is registered and may advertise")
            # should advertise
        pass

    def __check_neighbour(self, address):
        """
        It checks is the address in our neighbours array or not.

        :param address: Unknown address

        :type address: tuple

        :return: Whether is address in our neighbours or not.
        :rtype: bool
        """
        for node in self.stream.nodes:
            if node.get_server_address() == address:
                return True
        return False

    def __handle_message_packet(self, packet):
        """
        Only broadcast message to the other nodes.

        Warnings:
            1. Do not forget to ignore messages from unknown sources.
            2. Make sure that you are not sending a message to a register_connection.

        :param packet: Arrived message packet

        :type packet Packet

        :return:
        """
        # print ("handling received message. should broadcast.......")
        print("Broadcast MSG received from   ", packet.get_source_server_address())
        print(packet.get_body(), '\n\n')

        senders_address = packet.get_source_server_address()
        senders_node = self.stream.get_node_by_server(senders_address[0], senders_address[1])
        if senders_node == None:
            return
        message_packet = PacketFactory.new_message_packet(packet.get_body(), (self.server_ip, self.server_port))
        for node in self.stream.nodes:
            if node.set_register == True or node.get_server_address() == senders_address:
                continue
            self.stream.add_message_to_out_buff(node.get_server_address(), message_packet.get_buf())
        return

    def __handle_reunion_packet(self, packet):
        """
        In this function we should handle Reunion packet was just arrived.

        Reunion Hello:
            If you are root Peer you should answer with a new Reunion Hello Back packet.
            At first extract all addresses in the packet body and append them in descending order to the new packet.
            You should send the new packet to the first address in the arrived packet.
            If you are a non-root Peer append your IP/Port address to the end of the packet and send it to your parent.

        Reunion Hello Back:
            Check that you are the end node or not; If not only remove your IP/Port address and send the packet to the next
            address, otherwise you received your response from the root and everything is fine.

        Warnings:
            1. Every time adding or removing an address from packet don't forget to update Entity Number field.
            2. If you are the root, update last Reunion Hello arrival packet from the sender node and turn it on.
            3. If you are the end node, update your Reunion mode from pending to acceptance.


        :param packet: Arrived reunion packet
        :return:
        """


        senders_address = packet.get_source_server_address()
        # print("---------reunion packet recieved---------- ", senders_address)
        # print("packet header    ------  >    ", packet.get_header())
        # print("packet body    ------  >    lll", packet.get_body(), "lll")
        # print("packet addrss   ------ >     ", packet.get_source_server_address())

        if self.is_root and packet.get_body()[2] == 'Q':
            # set reunion time, send back packet, reverse array
            packet_body = packet.get_body()
            original_sender = (packet_body[5:20], packet_body[20:25])
            self.network_graph.find_node(original_sender[0], original_sender[1]).reunion_time = time.time()
            reversed_path = []
            body = packet_body[3:5]
            length = int(body)
            for i in range(length - 1, -1, -1):
                reversed_path.append((packet_body[(i * 20 + 5):((i + 1) * 20)], packet_body[((i + 1) * 20):((i + 1) * 20 + 5)]))
            print("Reunion packet received from   ", packet.get_source_server_address(), "  at root, reversed path = ", reversed_path)
            print(packet.get_buf(), '\n\n')

            reunion_back_packet = PacketFactory.new_reunion_packet('RES', (self.server_ip, self.server_port), reversed_path)
            print("Reunion response Packet sent from ", (self.server_ip, self.server_port), "    to    ",
                  packet.get_source_server_address())
            print(reunion_back_packet.get_buf(), '\n\n')

            self.stream.add_message_to_out_buff(senders_address, reunion_back_packet.get_buf())
        elif self.is_root == False and packet.get_body()[2] == 'Q':
            body = packet.get_body()
            length = int(body[4])
            path = []
            for i in range(length):
                path.append((body[(i * 20 + 5):((i + 1) * 20)], body[((i + 1) * 20):((i + 1) * 20 + 5)]))
            path.append((Node.parse_ip(self.server_ip), self.server_port))
            print("Reunion packet received from   ", packet.get_source_server_address(), "  , path = ", path)
            print(packet.get_buf(), '\n\n')

            reunion_forward_packet = PacketFactory.new_reunion_packet('REQ', (self.server_ip, self.server_port), path)
            print("Reunion forward Packet sent from ", (self.server_ip, self.server_port), "    to    ",
                  self.parents_address)
            print(reunion_forward_packet.get_buf(), '\n\n')

            self.stream.add_message_to_out_buff(self.parents_address, reunion_forward_packet.get_buf())
        elif self.is_root == False and packet.get_body()[2] == 'S':
            body = packet.get_body()
            length = int(body[3:5])
            if length > 1:
                print("Reunion respond packet received from   ", packet.get_source_server_address())
                print(packet.get_buf(), '\n\n')
                path = []
                for i in range(1, length):
                    path.append((body[(i * 20 + 5):((i + 1) * 20)], body[((i + 1) * 20):((i + 1) * 20 + 5)]))
                reunion_forward_packet = PacketFactory.new_reunion_packet('RES', (self.server_ip, self.server_port), path)
                self.stream.add_message_to_out_buff(path[0], reunion_forward_packet.get_buf())
                print("Reunion respond forward Packet sent from ", (self.server_ip, self.server_port), "    to    ", path[0])
                print(reunion_forward_packet.get_buf(), '\n\n')
            else:
                print("Reunion respond packet received from   ", packet.get_source_server_address(), "  to originial sender")
                print(packet.get_buf(), '\n\n')
                self.hello_back_received_time = time.time()

    def __handle_join_packet(self, packet):
        """
        When a Join packet received we should add a new node to our nodes array.
        In reality, there is a security level that forbids joining every node to our network.

        :param packet: Arrived register packet.


        :type packet Packet

        :return:
        """
        # TODO: Check if registered, if has already has node
        self.stream.add_node(packet.get_source_server_address())
        return

    def __get_neighbour(self, sender):
        """
        Finds the best neighbour for the 'sender' from the network_nodes array.
        This function only will call when you are a root peer.

        Code design suggestion:
            1. Use your NetworkGraph find_live_node to find the best neighbour.

        :param sender: Sender of the packet
        :return: The specified neighbour for the sender; The format is like ('192.168.001.001', '05335').
        """
        return self.network_graph.find_live_node(sender).address
