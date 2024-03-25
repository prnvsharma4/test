@app.route("/generate_chat_context", methods=["POST"])
def generate_chat_context():
    try:
        # Retrieve chat_id from session
        chat_id = session.get('chat_id', None)
        if not chat_id:
            return jsonify({"error": "chat_id is missing in session"}), 400

        # Fetch last N messages from chat history for context
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''SELECT message, is_user_message 
                          FROM vw_conv_history
                          WHERE chat_id = %s 
                          ORDER BY timestamp DESC 
                          LIMIT 4''', (chat_id,))
        chat_history = cursor.fetchall()
        cursor.close()

        
        # Format chat history into a GPT-compatible format
        context_messages = [f"{'User' if msg['is_user_message'] else 'Bot'}: {msg['message']}" for msg in chat_history[::-1]]  # Reverse to maintain chronological order
        context = "\n".join(context_messages)
        print("Context for chat_id", chat_id, ":\n", context)

        # Adjusted prompt with clear instruction
        gpt_prompt = f"Transform the essence of the following conversation into a FOUR-WORD or MAX 26 CHARACTERS action-oriented task summary. Ensure the summary is precise, relevant, and captures the key objective or outcome discussed. Conversation excerpt:\n{context}. If there is no conversation provided, please return Blank conversation. If task summary is exceeding 26 chars use ... after character 22 but DONOT exceed 26 characters"


        # Call the OpenAI API with the constructed prompt
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            max_tokens=7,  # Adjusted from 10 to 7 as an estimate
            temperature=0.0,  # Kept at 0 for determinism
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": gpt_prompt}
                ]
        )

        userid = session.get('userid', None)
        if not userid:
            return jsonify({"error": "userid is missing in session"}), 400
        # Process the response from OpenAI API
        response_content = ''
        if response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            if choice.message:
                response_content = choice.message.content.replace('\n', '<br>')
                print("Response Content:", response_content)
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('''INSERT INTO chat_context (userid, chat_id, context_summary, timestamp) 
                                  VALUES (%s, %s, %s, NOW())''', 
                               (userid, chat_id, response_content))
                mysql.connection.commit()
                cursor.close()

        # Return the extracted information as a JSON response

        return jsonify({
    "context_summary": response_content,  # Changed key from 'content' to 'context_summary'
})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"content": "An internal error occurred"}), 500

