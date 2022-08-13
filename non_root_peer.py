from Peer import Peer

if __name__ == "__main__":

    client = Peer("192.168.204.33", 31320, is_root=False, root_address=("192.168.203.167", 5353))

    client.t_run.start()
    client.start_user_interface()
    # client.run()
