class Server:


    apis = ['/api/v1/instance?',
            '/api/v1/nodeinfo?',
            '/nodeinfo/2.0?',
            '/nodeinfo/2.0.json?',
            '/nodeinfo/2.1.json?',
            '/main/nodeinfo/2.0?',
            '/api/statusnet/config?',
            '/api/nodeinfo/2.0.json?',
            '/api/nodeinfo?',
            '/wp-json/nodeinfo/2.0?',
            '/api/v1/instance/nodeinfo/2.0?',
            '/.well-known/x-nodeinfo2?'
            ]

    def __init__(self, name) -> None:
        self.name = name


    def node_info(self):
        ## get node software and such
        pass
