import "./chatPage.css";
import NewPrompt from "../../components/newPrompt/NewPrompt";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import Markdown from "react-markdown";
import { useAuth } from "@clerk/clerk-react";

const ChatPage = () => {
  const path = useLocation().pathname;
  const chatId = path.split("/").pop();
  const { getToken } = useAuth();

  const { isPending, error, data } = useQuery({
    queryKey: ["chat", chatId],
    queryFn: async () => {
      const token = await getToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/chats/${chatId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || "Failed to fetch chat");
      }

      return res.json();
    },
  });

  return (
    <div className="chatPage">
      <div className="wrapper">
        <div className="chat">
          {isPending ? (
            "Loading..."
          ) : error ? (
            <span style={{ color: "red" }}>Something went wrong!</span>
          ) : Array.isArray(data?.history) && data.history.length > 0 ? (
            data.history.map((message, i) => (
              <div
                key={i}
                className={message.role === "user" ? "message user" : "message"}
              >
                {message.parts[0].text.includes("<video") ? (
                  <div dangerouslySetInnerHTML={{ __html: message.parts[0].text }} />
                ) : (
                  <Markdown>{message.parts[0].text}</Markdown>
                )}
              </div>
            ))
          ) : (
            <span style={{ color: "#aaa" }}>No messages yet. Start the conversation below.</span>
          )}
          {data && <NewPrompt data={data} />}
        </div>
      </div>
    </div>
  );
};

export default ChatPage;