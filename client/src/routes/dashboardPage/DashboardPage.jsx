import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useOutletContext } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { useState, useEffect } from "react";  // <-- already added
import "./dashboardPage.css";

const chatTypes = [
  "Story Generation",
  "RAG Story Generation",
  "Video Generation (Static)",
  "Video Generation (Fluid)",
  "History ChatBot",
];

const DashboardPage = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { getToken } = useAuth();
  const { selectedType, setSelectedType } = useOutletContext();

  const [placeholderText, setPlaceholderText] = useState("");
  const [isLoading, setIsLoading] = useState(false); // <-- added

  useEffect(() => {
    if (
      selectedType === "Story Generation" ||
      selectedType === "RAG Story Generation" ||
      selectedType === "Video Generation (Static)" ||
      selectedType === "Video Generation (Fluid)"
    ) {
      setPlaceholderText("ایک ایسی کہانی لکھیں....");
    } else if (selectedType === "History ChatBot") {
      setPlaceholderText("تاریخ سے متعلق اپنا سوال پوچھیں");
    }
  }, [selectedType]);

  const mutation = useMutation({
    mutationFn: async (inputText) => {
      const token = await getToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/chats`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text: inputText, type: selectedType }),
      });

      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: async (chatId) => {
      await queryClient.invalidateQueries({ queryKey: ["userChats", selectedType] });
      setIsLoading(false); // <-- stop loading
      navigate(`/dashboard/chats/${chatId}`);
    },
    onError: (error) => {
      setIsLoading(false); // <-- stop loading
      console.error("❌ Chat creation error:", error.message);
      alert("Something went wrong. Please try again.");
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = e.target.text.value.trim();
    if (!text) return;
    setIsLoading(true);  // <-- start loading
    mutation.mutate(text);
    e.target.reset();
  };

  return (
    <div className="dashboardPage">
      {/* Top-left dropdown */}
      <select
        className="chat-type-dropdown"
        value={selectedType}
        onChange={(e) => setSelectedType(e.target.value)}
      >
        {chatTypes.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>

      <div className="texts">
        <div className="logo">
          <img src="/logo.png" alt="Logo" />
          <h1>ASH AI</h1>
        </div>
        <div className="options">
          <div className="option">
            <img src="/chat.png" alt="Chat" />
            <span>تخیل آپ کی انگلیوں پر</span>
          </div>
        </div>
      </div>

      <div className="formContainer">
        {isLoading ? (
          <div className="loading-animation">
            <img src="/loading.gif" alt="Loading..." />
            <p>جواب تیار کیا جا رہا ہے...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <input
              type="text"
              name="text"
              placeholder={placeholderText}
            />
            <button type="submit">
              <img src="/arrow.png" alt="Send" />
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
