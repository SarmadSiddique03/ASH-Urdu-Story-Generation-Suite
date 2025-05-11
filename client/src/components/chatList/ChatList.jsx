import { Link } from "react-router-dom";
import "./chatList.css";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/clerk-react";

const ChatList = ({ selectedType }) => {
  const { getToken } = useAuth();

  const { isPending, error, data } = useQuery({
    queryKey: ["userChats", selectedType],
    queryFn: async () => {
      const token = await getToken();
      const url = `${import.meta.env.VITE_API_URL}/api/userchats?type=${encodeURIComponent(
        selectedType
      )}`;

      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const message = await res.text();
        throw new Error(message || "Failed to fetch user chats");
      }

      return res.json();
    },
    enabled: !!selectedType,
    staleTime: 10000,
  });

  return (
    <div className="chatList">
      <span className="title">DASHBOARD</span>
      <Link to="/dashboard">Create a new Chat</Link>
      <Link to="/explore-ash">Explore ASH AI</Link>
      <hr />
      <span className="title">RECENT CHATS</span>
      <div className="list">
        {isPending ? (
          "Loading..."
        ) : error ? (
          <span style={{ color: "red" }}>Something went wrong!</span>
        ) : Array.isArray(data) && data.length > 0 ? (
          [...data]
            .reverse()
            .map((chat) => (
              <Link to={`/dashboard/chats/${chat._id}`} key={chat._id}>
                {chat.title || "Untitled Chat"}
              </Link>
            ))
        ) : (
          <span style={{ color: "#999" }}>No chats found.</span>
        )}
      </div>
      <hr />
      <div className="upgrade">
        <img src="/logo.png" alt="ASH AI Logo" />
        <div className="texts">
          <span>ASH AI</span>
          <span>Unleash your creativity</span>
        </div>
      </div>
    </div>
  );
};

export default ChatList;
