from neo4j import GraphDatabase, RoutingControl
from dotenv import load_dotenv
import os
import logging

log = logging.getLogger(__name__)

class Db:

    def __init__(self):
        load_dotenv()
        api_uri = os.getenv("NEO4J_URI")
        api_usr = os.getenv("NEO4J_USR")
        api_secret = os.getenv("NEO4J_PW")
        log.debug(api_uri)
        self.driver = GraphDatabase.driver(api_uri, auth=(api_usr, api_secret))

    def close(self):
        self.driver.close()
#    def driver(self):
        

    def add_user(self, user):
        self.driver.execute_query("""MERGE (server:Server {url:$server})
            MERGE (a:User {uri: $uri})
            MERGE (a)-[:IN_COMMUNITY]-(server)
            SET a.name=$name, a.server=$server RETURN a, server""",
            name=user.name, uri=user.uri, server=user.server, database_="neo4j",
        )

    def add_follower(self, user, follower):
        self.driver.execute_query("MERGE (u:User {uri: $usr})"
                                  "MERGE (f:User {uri: $ff})"
                                  "MERGE (f)-[:FOLLOWS]->(u)",
                                  usr=user,
                                  ff=follower,
                                  database_="neo4j")

    def add_followers(self, usr, followers):
        for f in followers:
            self.add_follower(usr, f)
            
    def add_following(self, usr, following):
        for f in following:
            self.add_follower(f, usr)
            
    def update_follow_count(self, user, count, fwer_or_fwing):
        
        self.driver.execute_query("MATCH (u:User {uri: $usr})"
                                  "SET u." + fwer_or_fwing + " = $c",
                                  usr=user,
                                  ff=fwer_or_fwing,
                                  c=count,
                                  database_="neo4j")

    def get_user_in_degree(self, user):
        
        records, _, _ = self.driver.execute_query("MATCH (u:User {uri: $usr})<-[f:FOLLOWS]-(:User) RETURN count(f) AS count",
                                  usr=user,database="neo4j", routing_=RoutingControl.READ)
        return records

    def get_user_out_degree(self, user):
        
        records, _, _ = self.driver.execute_query("MATCH (u:User {uri: $usr})-[f:FOLLOWS]->() RETURN count(f) AS count",
                                  usr=user,database="neo4j", routing_=RoutingControl.READ)
        return records

    def get_unscraped_nodes(self, round):
        log.info("ROUND: %s", round)
        records, _, _ = self.driver.execute_query("""
                    WITH $this_round as this_round
                    MATCH (u:User)-[f:SCRAPED_ON]->(r:Round WHERE r.id < this_round)
                    RETURN u.uri as uri
                    ORDER  BY r  LIMIT 500
                    UNION ALL
                    MATCH (u:User) WHERE NOT (u)-[]->(:Round)
                    RETURN u.uri as uri
                    LIMIT 500""",
                            this_round=round, database="neo4j", routing_=RoutingControl.READ)
        
        return [record['uri'] for record in records]
        
    def set_user_round(self, user, round):
        self.driver.execute_query("MERGE (u:User {uri: $usr})"
                                  "MERGE (f:Round {id: $rnd})"
                                  "MERGE (u)-[:SCRAPED_ON]->(f)",
                                  usr=user,
                                  rnd=round,
                                  database_="neo4j")        
        
    def set_dead_server(self, server, round):
        self.driver.execute_query("MERGE (u:Server {url: $url})"
                                  "MERGE (f:Round {id: $rnd})"
                                  "MERGE (u)-[:DEAD_ON]->(f)",
                                  url=server,
                                  rnd=round,
                                  database_="neo4j")
        
    def set_dead_user(self, user, round):
        self.driver.execute_query("MERGE (u:User {uri: $url})"
                                  "MERGE (f:Round {id: $rnd})"
                                  "MERGE (u)-[r:SCRAPED_ON]->(f)"
                                  "SET r.usr_status = 'NOT REACHABLE'",
                                  url=user,
                                  rnd=round,
                                  database_="neo4j")       
    def get_deg_centrality(self):
        self.driver.execute_query("""CALL gds.graph.project(
                                                          'myGraph',
                                                          'User',
                                                          {
                                                            FOLLOWS: {
                                                              orientation: 'REVERSE'
                                                            }
                                                          }
                                                        )""",
                                  database_="neo4j")
        records, _, _  = self.driver.execute_query("""CALL gds.degree.stream('myGraph')
                                    YIELD nodeId, score
                                    RETURN gds.util.asNode(nodeId).uri AS usr, score  AS followers
                                    ORDER BY followers DESC, usr DESC
                                    LIMIT 10""",
                                  database_="neo4j")
        self.driver.execute_query("""CALL gds.graph.drop('myGraph', false)""",
                                  database_="neo4j")
        return [(record['usr'], record['followers']) for record in records]
        
    @staticmethod
    def _create_and_return_greeting(tx, message):
        result = tx.run("CREATE (a:Greeting) "
                        "SET a.message = $message "
                        "RETURN a.message + ', from node ' + id(a)", message=message)
        return result.single()[0]