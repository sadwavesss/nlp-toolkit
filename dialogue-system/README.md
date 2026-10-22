# Dialogue System "Animals of the World"

Task-oriented chatbot that answers questions about animals: descriptions, habitat, diet, facts and comparisons.

## Architecture

| Component | File | Role |
|---|---|---|
| NLU | `nlp_processor.py` | intent classification with prioritized patterns; entity extraction (ANIMAL, HABITAT, CATEGORY) with a word-form dictionary and spaCy lemmatization; confidence score |
| Dialogue manager | `app.py` | per-session dialogue state, remembers the last animal for follow-up questions |
| Knowledge base | `database_manager.py` | animals, dialogues and messages in SQLite |
| NLG | `response_generator.py` | template-based answers, comparison tables |
| UI | `templates/`, `static/` | chat, dialogue history with statistics, animal catalog, help |

Intents: `greeting`, `goodbye`, `animal_info`, `habitat_query`, `diet_query`, `facts_query`, `compare_animals`, `unknown`
(see [docs/intents.png](docs/intents.png)).

The system was designed first ([design/docs](design/docs): conceptual, logical and physical dialogue models, dialogue
flow, data structures, interface layout in PlantUML) and then implemented ([docs](docs): functional and structural
schemes, message flow, ER diagram).

## REST API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/send_message` | send a message, get the answer with intent and entities |
| GET | `/api/get_history` | current dialogue |
| POST | `/api/new_dialogue`, `/api/end_dialogue` | dialogue lifecycle |
| GET | `/api/dialogues`, `/api/dialogue/<id>` | dialogue history |
| GET | `/api/animals`, `/api/statistics` | knowledge base and usage statistics |

## Run

```bash
pip install -r requirements.txt
python -m spacy download ru_core_news_sm
python app.py            # http://127.0.0.1:5003
```
