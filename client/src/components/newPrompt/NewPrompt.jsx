// src/components/newPrompt/NewPrompt.jsx
import { useEffect, useRef, useState } from "react";
import "./newPrompt.css";
import Markdown from "react-markdown";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/clerk-react";

const NewPrompt = ({ data }) => {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer]     = useState("");
  const endRef                  = useRef(null);
  const formRef                 = useRef(null);

  const queryClient = useQueryClient();
  const { getToken } = useAuth();

  const singleTurnTypes = [
    "Story Generation",
    "RAG Story Generation",
    "Video Generation (Static)",
    "Video Generation (Fluid)",
  ];
  const isSingleTurn    = singleTurnTypes.includes(data?.type);
  const alreadyAnswered = data?.history?.length > 1;

  // auto-scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [data, question, answer]);

  // ─── send user question ────────────────────────────────────────────────────────────
  const mutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/api/chats/${data._id}/message`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ question: question || undefined }),
        }
      );
      if (!res.ok) throw new Error(await res.text());
      const { answer } = await res.json();
      return answer;
    },
    onSuccess: async (fullText) => {
      setAnswer(fullText);
      await queryClient.invalidateQueries({ queryKey: ["chat", data._id] });
      formRef.current?.reset();
      setQuestion("");
    },
    onError: (err) => {
      console.error(err);
      alert("Something went wrong while generating the answer.");
    },
  });

  // ─── download PDF ─────────────────────────────────────────────────────────────────
  const handleDownload = async () => {
    try {
      const token = await getToken();
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/api/chats/${data._id}/pdf`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error("Could not download PDF");
      const blob = await res.blob();
      const url  = window.URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `story_${data._id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert("Failed to download PDF");
    }
  };

  // ─── form submit ──────────────────────────────────────────────────────────────────
  const handleSubmit = (e) => {
    e.preventDefault();
    const text = e.target.text.value.trim();
    if (!text) return;
    setQuestion(text);
    e.target.text.value = "";
    mutation.mutate();
  };

  // ─── EARLY RETURN FOR HISTORY CHATBOT ───────────────────────────────────────────────
  if (data.type === "History ChatBot") {
    return (
      <>
        {/* immediately render user's question */}
        {question && <div className="message user">{question}</div>}

        {/* buffer */}
        <div className="endChat" ref={endRef} />

        {/* always show form */}
        <form className="newForm" onSubmit={handleSubmit} ref={formRef}>
          <input type="text" name="text" placeholder="مزید پوچھیں...." />
          <button type="submit">
            <img src="/arrow.png" alt="Send" />
          </button>
        </form>
      </>
    );
  }

  // ─── FALLBACK FOR SINGLE-TURN (Story/RAG/Video) ──────────────────────────────────
  return (
    <>
      {/* show the user’s latest question */}
      {question && <div className="message user">{question}</div>}

      {/* show the model’s answer */}
      {answer && (
        <div className="message">
          {answer.includes("<video")
            ? <div dangerouslySetInnerHTML={{ __html: answer }} />
            : <Markdown>{answer}</Markdown>}
        </div>
      )}

      {/* buffer */}
      <div className="endChat" ref={endRef} />

      {/* once answered, swap to Download + “new chat” warning */}
      {isSingleTurn && alreadyAnswered ? (
        <>
          {(data.type === "Story Generation" || data.type === "RAG Story Generation") && (
            <button className="download-btn" onClick={handleDownload}>
              ڈاؤن لوڈ کریں (PDF)
            </button>
          )}
          <div className="message warning">
            نئی کہانی یا ویڈیو تیار کرنے کے لیے، براہ کرم ایک نئی چیٹ شروع کریں۔
          </div>
        </>
      ) : (
        <form className="newForm" onSubmit={handleSubmit} ref={formRef}>
          <input type="text" name="text" placeholder="مزید پوچھیں...." />
          <button type="submit">
            <img src="/arrow.png" alt="Send" />
          </button>
        </form>
      )}
    </>
  );
};

export default NewPrompt;
