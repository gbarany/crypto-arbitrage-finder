class FWLiveParams:
    neo4j_mode_disabled = 1
    neo4j_mode_localhost = 2
    neo4j_mode_aws_cloud = 3

    def __init__(self,
                 enable_plotting=True,
                 is_sandbox_mode=True,
                 is_forex_enabled=True,
                 results_dir='./',
                 neo4j_mode=neo4j_mode_disabled):
        self.enable_plotting = enable_plotting
        self.is_sandbox_mode = is_sandbox_mode
        self.is_forex_enabled = is_forex_enabled
        self.results_dir = results_dir
        self.neo4j_mode = neo4j_mode
