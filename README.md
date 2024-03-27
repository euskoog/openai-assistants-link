# OpenAI Assistants Link + LLM Evaluator Server Template

_REST API for connecting to the OpenAI Assistants API and storing base-level evals._

---

[![Twitter Follow](https://img.shields.io/twitter/follow/euskoog?style=social)](https://twitter.com/euskoog)

## ❓ What This Is

OpenAI Assistants Link is a repo for linking local resources to the OpenAI Assistants API for leveraging and scaling assistant capabilities. This repo acts as a template for research or enterprise devs trying to scale the use of OpenAI assistants within their organization.

OpenAI Assistants Link also offers a base-level approach to evaluating LLM responses from the Assistants API. These evaluations should act as a guideline for how to begin your aproach to LLM evals and should be modified to best fit your needs.

You will probably find this repo useful if one or more of these points apply:

- You are at a company that wants to use OpenAI and you have little experience with it.
- You are at a company that wants to automate customer experiences with chatbots.
- You have automated customer experiences with chatbots but have no testing/evaluation criteria.
- You like learning!

While you are here, please consider checking out these other resources to better enhance your understanding of LLM usage and evaluations:

- [Instructor (Structured LLM Output)](https://github.com/jxnl/instructor)
- [LlamaIndex (Evaluating Responses)](https://docs.llamaindex.ai/en/stable/module_guides/evaluating/root.html)
- [Evaluating RAG Applications with RAGAs](https://towardsdatascience.com/evaluating-rag-applications-with-ragas-81d67b0ee31a)

## ❗ What This Is NOT

- Comprehensive!

  - This template is not a one-size-fits-all solution. It focuses on providing a starting point for developers interested in leveraging OpenAI Assistants.
  - A good evaluation system focuses on far more than just semantics at message-level, ideally you would have additional evals in place for:

    - RAG Evaluation (as a system)
    - Assistant Tone
    - Response Length
    - etc...

  - All of this above requires a lot of time and data. I hope that what I have can help get you over the hump of managing product requirements and expectations. It's better to have something than nothing.

## 🚀 Getting Started

1. **Deployment:** First, you will need to deploy the API to Railway (or whatever hosting service you fancy). Please follow the instructions in the section below for deploying to Railway.

2. **Clone and Set Up**: Start by cloning this repository locally. Install the required dependencies using

```
pip install -r requirements.txt
```

3. **If you are using Prisma for ORM** you will need to run

```
prisma db push
```

&nbsp; to push the database schema, and

```
prisma generate
```

&nbsp; to generate the model schemas for runtime. See `prisma/schema.prisma` for schema details and DB connections.

4. **Run Locally**: Launch your FastAPI server with Uvicorn using the command:

```
uvicorn app.main:app --reload --port 8000
```

&nbsp; This setup provides hot-reloading for development ease.

5. **Add Local Variables**: To run this server locally you will need 4 variables.

- `OPENAI_API_KEY` Needed for all LLM activities, including chat/eval
- `DATABASE_URL` A link to your postgres (or other) database. See Railway setup for more

&nbsp; Optional (only used to create API routes)

- `API_PREFIX_V1=/api/v1`
- `BASE_URL=http://127.0.0.1:8000`

## 🌐 Deploy on Railway

### API Deployment

Deploying on Railway is straightforward:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/-M8zbi?referralCode=Ma0xP7)

1. Click the "Deploy on Railway" button to start.
2. Follow the prompts to configure and deploy your FastAPI server.
3. If this process fails, you can always clone this project locally and import it to Railway through Github.

### Database Deployment

For this project, you will also need your own database. I recommend using railway for this as well to set up a Postgres connection.

In the same dashboard that you hosted the API in, navigate to `New -> Database -> Add PostgreSQL` in the top right corner.

To get connection details for your new DB, click on the Postgres container and navigate to `Variables`.

Your view should look like this:

![image](/public/Postgres.png)

Once you have your DB connection string, add it to your FastAPI container as `DATABASE_URL`.

Here is an example of my connections:

![image](/public/FastAPI-vars.png)

## 📖 Examples

At this point, I'm assuming that you have successfully deployed the API, or you're running it locally. Now to have some fun!

### Creating Default Categories for Evaluations

The first thing that we need to do is create our categories for evaluation. We need to make these 'default' categories for usage tracking,
so that our evaluation process has context on how to categorize queries. To do this, we need to navigate to:

`YOUR_BASE_URL/api/v1/core/docs#/categories/categories-Create%20category`

This POST request should be used to seed all the default categories that you want to track.

![image](/public/swagger-category.png)

If you want to use the defaults that I have on [my evaluation dashboard](https://openai-assistants-evals-dash.vercel.app/evals), then reference the defaults from my blogpost below:

![image](/public/categories.png)

### Creating and Chatting With an Assistant

Once you have your categories set up, we can start chatting!

#### 1. Create your Assistant

To create an OpenAI Assistant, navigate to

`YOUR_BASE_URL/api/v1/core/docs#/assistants/assistants-Create%20assistant`

Here you can create a new assistant with a name and custom instructions.

#### 2. Add documents to your Assistant (Optional, but recommended)

If you want your assistant to use documents for context retrieval, navigate to

`YOUR_BASE_URL/api/v1/core/docs#/datasources/datasources-Create%20document%20datasource`

Once you have created a datasource, we need to link it to the correct assistant. To do so, we need to combine

- Assistant ID (from your new assistant)
- Datasource ID (from your new uploaded document)

With both of these IDs, we can navigate to

`YOUR_BASE_URL/api/v1/core/docs#/assistant-datasources/assistant-datasources-Create%20assistant%20datasource`

It is at this endpoint where you can connect both entities together with a JOIN table.

![image](/public/assistant-ds.png)

Once you create an Assistant Datasource, you should be ready to chat!

##### Note: If you need sample documents to test, I have some examples in the public/sample_docs directory.

#### 3. Chat with your Assistant

Chatting with your assistant is easy and only requires three things:

- Assistant ID
- Message
- Conversation ID (Optional)

To view the Assistant Chat endpoint, navigate to

`YOUR_BASE_URL/api/v1/core/docs#/assistants/assistants-Chat%20with%20an%20assistant`

Here, you can provide whatever you want and run your query with the evaluator. The messages will be saved in the Conversation table and evaluated by default, so there is no need to run that process on your own.

![image](/public/chat.png)

If you leave the conversation ID empty, the chat endpoint will generate a new conversation on the request.

## 📝 Notes

- I love feedback. Please visit the [Discussions Tab](https://github.com/euskoog/openai-assistants-link/discussions) if you want to talk about something.
- To learn about how to use FastAPI with most of its features, you can visit the [FastAPI Documentation](https://fastapi.tiangolo.com/tutorial/)
- To learn about how to use the OpenAI Assistants API, you can visit the [OpenAI Assistants Documentation](https://platform.openai.com/docs/api-reference/assistants)
