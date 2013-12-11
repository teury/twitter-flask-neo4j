from py2neo import neo4j
from py2neo import node, rel

graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")
#graph_db.clear()
user = graph_db.get_or_create_index(neo4j.Node, "User")
post = graph_db.get_or_create_index(neo4j.Node, "Post")


class User():

    @classmethod
    def get_user_by_name(self, username):
        u = user.get("username", username)[0]
        return u   

    @classmethod
    def get_user_id(self,username):
        u = user.get("username", username)
        if u:
            u=u[0]
            if u:
                return u._id
        else:
            return []

    @classmethod
    def get_user_by_id(self, user_id):
        u = graph_db.node(user_id)
        return u


    @classmethod
    def login(self, username):
        u = user.get("username", username)
        if u:
            u=u[0]
            return u
        else:
            return None

    @classmethod
    def register(self, username, email, password):
        u = user.get_or_create("username", username, {
            "username": username, "email": email, "password": password,
        })

        graph_db.create( rel( u, "FOLLOWED", u ) )

        return u

    @classmethod
    def followed(self, user_1, user_2):
        u1=graph_db.node(user_1)
        u2=graph_db.node(user_2)
        rels = graph_db.match_one(start_node=u1, end_node=u2, rel_type="FOLLOWED")
                
        return rels

    @classmethod
    def following(self, user_1, user_2):
        u1=graph_db.node(user_1)
        u2=graph_db.node(user_2)
        graph_db.create( rel( u1, "FOLLOWED", u2 ) )


    @classmethod
    def unfollowing(self, user_1, user_2):
        u1=graph_db.node(user_1)
        u2=graph_db.node(user_2)
        rels = graph_db.match_one(start_node=u1, end_node=u2, rel_type="FOLLOWED")
        rels.delete()


    @classmethod
    def followed_by_user(self, user):
        query_string = """
            start u=node(%d)
            match (user)-[:FOLLOWED]->(u)
            where ID(user) <> ID(u)
            return user.email as email, user.username as username;
        """ % (user)

        result = neo4j.CypherQuery(graph_db, query_string).execute()

        return result

    @classmethod
    def following_by_user(self, user):
        query_string = """
            start u=node(%d) 
            match (u)-[:FOLLOWED]->(user) 
            where ID(user) <> ID(u)
            return user.email as email, user.username as username;
        """ % (user)

        result = neo4j.CypherQuery(graph_db, query_string).execute()
        return result

    @classmethod
    def recommend_user(self, user):
        query_string = """
            START vahid=node(%d) 
            MATCH (vahid)-[:FOLLOWED*2..2]->(ff) 
            WHERE NOT (vahid)-[:FOLLOWED]->(ff) 
            RETURN COUNT(*) as mf, ff.username as username, ff.email as email;
        """ % (user)

        result = neo4j.CypherQuery(graph_db, query_string).execute()
        #if len(result) == 0:
        #    print "going to get following user"
        #    query_string = """
        #        START vahid=node(%d) 
        #        MATCH (ff)-[:FOLLOWED]->(vahid) 
        #        WHERE NOT (vahid)-[:FOLLOWED]->(ff) 
        #        RETURN COUNT(*) as mf, ff.username as username, ff.email as email;
        #    """ % (user)

        #    result = neo4j.CypherQuery(graph_db, query_string).execute()

        return result


class Post():

    @classmethod
    def create(self, text, date, user_id):
        #alice, = graph_db.create({"name": "Alice"})
        user_obj = graph_db.node(user_id)
        u = graph_db.create(node({"text": text,"date": date}), rel(user_obj, 'POSTED', 0))

    @classmethod
    def timeline_following(self, user_id):
        query_string = """
            start cur_user=node(%d)
            match cur_user-[:FOLLOWED]->(user)-[:POSTED]->(post)-[r?:LIKE]-()
            return
            count(r) as cnt_like,
            post.text as text,
            ID(post) as post_id,
            ID(user) as user_id,
            user.username as username,
            user.email as email,
            post.date as date
            order by post.date desc;
        """ % (user_id)

        result = neo4j.CypherQuery(graph_db, query_string).execute()

        return result

    @classmethod
    def timeline(self):
        query_string = """
            START user=node(*)
            MATCH (user)-[:POSTED]->(post)-[r?:LIKE]-()
            RETURN
            count(r) as cnt_like,
            post.text as text,
            ID(post) as post_id,
            ID(user) as user_id,
            user.username as username,
            user.email as email,
            post.date as date

            ORDER BY post.date DESC;
        """

        result = neo4j.CypherQuery(graph_db, query_string).execute()

        return result

    @classmethod
    def timeline_user(self, user_id):
        query_string = """
            START user=node(%d)
            MATCH (user)-[:POSTED]->(post)-[r?:LIKE]-()
            RETURN
            count(r) as cnt_like,
            post.text as text,
            ID(post) as post_id,
            ID(user) as user_id,
            user.username as username,
            user.email as email,
            post.date as date
            ORDER BY post.date DESC;
        """ % (user_id)

        result = neo4j.CypherQuery(graph_db, query_string).execute()

        return result

    @classmethod
    def like(self, post_id, user_id):
        user = graph_db.node(user_id)
        post = graph_db.node(post_id)
        rels = graph_db.match_one(start_node=user, end_node=post, rel_type="LIKE")
        if not rels:
            graph_db.create( rel( user, "LIKE", post ) )

    @classmethod
    def cnt_like(self, post_id):
        query_string = "start n=node(%d) match n-[:LIKE]-() return count(*);" % post_id

