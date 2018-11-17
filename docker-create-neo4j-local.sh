docker run -d \
    --publish=7474:7474 --publish=7687:7687 \
    --volume=$HOME/neo4j/data:/data \
    --volume=$HOME/neo4j/plugins:/plugins \
    --volume=$HOME/neo4j/logs:/logs \
    --env=NEO4J_dbms_security_procedures_unrestricted=algo.*,apoc.trigger.*,apoc.meta.*,apoc.\\\* \
    neo4j:3.4.9