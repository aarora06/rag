import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import FileUploadComponent from './FileUploadComponent';

// Replace with your actual API endpoint and API Key
const API_URL = 'http://127.0.0.1:8000/chat/'; // Or your deployed backend URL
const API_KEY = 'mu4jLFQ3IYFhYxj0ymBRqKgTkDxuadYdds2tkWSm'; // Replace with the API key from your backend

// Define types for better type safety
type Message = {
  sender: 'user' | 'ai';
  text: string;
};

function ChatComponent() {
  // State to hold the current user input
  const [input, setInput] = useState<string>('');
  // State to hold the chat history (list of message objects: {sender: 'user' | 'ai', text: string})
  const [chatHistory, setChatHistory] = useState<Message[]>([]);
  // State to manage loading state while waiting for API response
  const [isLoading, setIsLoading] = useState<boolean>(false);
  // Ref for auto-scrolling to the latest message
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  // Chat context fields
  const [company, setCompany] = useState('');
  const [department, setDepartment] = useState('');
  const [employee, setEmployee] = useState('');

  // Function to scroll to the bottom of the chat messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Scroll to bottom whenever chat history updates
  useEffect(scrollToBottom, [chatHistory]);

  // Function to handle sending a message
  const sendMessage = async () => {
    if (input.trim() === '') return; // Don't send empty messages

    const userMessage = input.trim();
    setChatHistory(prevHistory => [...prevHistory, { sender: 'user', text: userMessage }]);
    setInput('');
    setIsLoading(true);

    try {
      // Prepare the chat history format for the API
      const apiChatHistory = chatHistory.map(msg => [msg.sender === 'user' ? msg.text : '', msg.sender === 'ai' ? msg.text : '']);
      const historyToSend = [...apiChatHistory, [userMessage, '']];

      const payload: any = {
        question: userMessage,
        chat_history: historyToSend.filter(pair => pair[0] !== '' || pair[1] !== '')
      };
      if (company.trim()) payload.company = company.trim();
      if (department.trim()) payload.department = department.trim();
      if (employee.trim()) payload.employee = employee.trim();

      const response = await axios.post(
        API_URL,
        payload,
        {
          headers: {
            'X-API-Key': API_KEY,
            'Content-Type': 'application/json',
            'accept': 'application/json',
          },
        }
      );

      const updatedHistoryFromApi: [string, string][] = (response.data as { chat_history: [string, string][] }).chat_history;
      const newChatHistory: Message[] = updatedHistoryFromApi
        .map(([q, a]) => [
          q ? { sender: 'user', text: q } : null,
          a ? { sender: 'ai', text: a } : null
        ])
        .flat()
        .filter((msg): msg is Message => !!msg);
      setChatHistory(newChatHistory);
    } catch (error: any) {
      console.error('Error sending message:', error);
      let errorMessage = 'An error occurred while fetching the response.';
      if (error.response) {
        errorMessage = `Error: ${error.response.status} - ${error.response.data?.detail?.error || error.response.statusText}`;
      } else if (error.request) {
        errorMessage = 'Error: No response received from the server.';
      }
      setChatHistory(prevHistory => [...prevHistory, { sender: 'ai', text: errorMessage }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle key press (Enter to send message)
  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !isLoading) {
      sendMessage();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '20px', maxWidth: '800px', margin: 'auto', border: '1px solid #ccc', borderRadius: '8px' }}>
      <FileUploadComponent />
      <div style={{ marginBottom: '12px', display: 'flex', gap: '8px' }}>
        <input
          type="text"
          placeholder="Company (optional for chat)"
          value={company}
          onChange={e => setCompany(e.target.value)}
          disabled={isLoading}
        />
        <input
          type="text"
          placeholder="Department (optional)"
          value={department}
          onChange={e => setDepartment(e.target.value)}
          disabled={isLoading}
        />
        <input
          type="text"
          placeholder="Employee (optional)"
          value={employee}
          onChange={e => setEmployee(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <h2 style={{ textAlign: 'center' }}>Chat with AI</h2>
      <div style={{ flexGrow: 1, overflowY: 'auto', marginBottom: '10px', paddingRight: '10px' }}>
        {chatHistory.map((message, index) => (
          <div key={index} style={{ marginBottom: '10px', textAlign: message.sender === 'user' ? 'right' : 'left' }}>
            <span style={{
              display: 'inline-block',
              padding: '8px 12px',
              borderRadius: '15px',
              backgroundColor: message.sender === 'user' ? '#007bff' : '#f1f0f0',
              color: message.sender === 'user' ? 'white' : 'black'
            }}>
              {message.text}
            </span>
          </div>
        ))}
        {/* Dummy element to scroll to */}
        {isLoading && (
          <div style={{ marginBottom: '10px', textAlign: 'left' }}>
            <span style={{
              display: 'inline-block',
              padding: '8px 12px',
              borderRadius: '15px',
              backgroundColor: '#f1f0f0',
              color: 'black'
            }}>
              Thinking...
            </span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div style={{ display: 'flex' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Type your message..."
          style={{ flexGrow: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc', marginRight: '10px' }}
          disabled={isLoading}
        />
        <button
          onClick={sendMessage}
          style={{ padding: '10px 20px', borderRadius: '4px', border: 'none', backgroundColor: '#007bff', color: 'white', cursor: isLoading ? 'not-allowed' : 'pointer' }}
          disabled={isLoading}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatComponent;