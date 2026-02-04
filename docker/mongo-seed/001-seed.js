// Seed MongoDB knowledge base for HelloBot
db = db.getSiblingDB("hellobot_knowledge");

const seed = JSON.parse(cat("/docker-entrypoint-initdb.d/../mongo_seed.json"));

for (const [collectionName, docs] of Object.entries(seed)) {
  db[collectionName].insertMany(docs);
}

