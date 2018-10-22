class FWLiveParams:
    neo4j_mode_disabled = 1
    neo4j_mode_localhost = 2
    neo4j_mode_aws_cloud = 3

    neo4j_mode_localhost_details = {
        'uri' : 'bolt://localhost:7687',
        'user' : 'neo4j',
        'password' : 'neo' 
        }

    neo4j_mode_aws_cloud_details = {
        'uri' : 'bolt://3.120.197.59:7687',
        'user' : 'neo4j',
        'password' : 'i-0eb8e05bdc700631a' 
        }

    def __init__(self,
                 enable_plotting=True,
                 remoteDebuggingEnabled=False,
                 is_sandbox_mode=True,
                 is_forex_enabled=True,
                 results_dir='./',
                 neo4j_mode=neo4j_mode_disabled):
        self.enable_plotting = enable_plotting
        self.is_sandbox_mode = is_sandbox_mode
        self.is_forex_enabled = is_forex_enabled
        self.results_dir = results_dir
        self.neo4j_mode = neo4j_mode
        self.remoteDebuggingEnabled=remoteDebuggingEnabled
        

        