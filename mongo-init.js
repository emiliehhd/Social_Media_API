// initialisation MongoDB
// S'exécute au premier démarrage 

db = db.getSiblingDB('MySocialNetwork_project_DB');

// Créer des collections avec validation
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["email", "username", "hashed_password"],
      properties: {
        email: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        username: {
          bsonType: "string",
          description: "must be a string and is required"
        }
      }
    }
  }
});

db.createCollection("events");
db.createCollection("groups");
db.createCollection("discussions");
db.createCollection("messages");
db.createCollection("albums");
db.createCollection("photos");
db.createCollection("comments");
db.createCollection("polls");
db.createCollection("votes");
db.createCollection("ticket_types");
db.createCollection("tickets");
db.createCollection("shopping_items");
// db.createCollection("carpools");

print("Database initialized ");