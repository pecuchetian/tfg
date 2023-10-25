from neo4j import GraphDatabase


URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "password")

class Db:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "***REMOVED***"))

    def close(self):
        self.driver.close()

from neo4j import GraphDatabase, RoutingControl



    @staticmethod
    def _create_and_return_greeting(tx, message):
        result = tx.run("CREATE (a:Greeting) "
                        "SET a.message = $message "
                        "RETURN a.message + ', from node ' + id(a)", message=message)
        return result.single()[0]