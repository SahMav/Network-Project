from Peer import Peer

if __name__ == "__main__":

    server = Peer("127.000.000.001", 5355, is_root=True)

    server.t_run.start()
    server.start_user_interface()

    # server.run()
