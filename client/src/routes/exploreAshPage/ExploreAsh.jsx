import {useState} from "react";
import {LayoutGroup, AnimatePresence, motion} from "framer-motion";
import {TypeAnimation} from "react-type-animation";
import "./exploreAsh.css";

const modelsInfo = [{
    name: "Story Generation",
    type: "story",
    description: "Creates beautiful stories written in Urdu. Designed for fluent, expressive storytelling.",
    prompt: "ایک پرانا صندوقچہ آپ کے گھر کے اٹاری میں ملتا ہے۔ جب آپ اسے کھولتے ہیں، تو آپ کو ایک ایسی چیز ملتی ہے جو آپ کی زندگی ہمیشہ کے لیے بدل دیتی ہے۔",
    output: `میرے گھر کے اٹاری میں ایک پرانی صندوقچہ تھی جو سالوں سے کبھی بھی کھولا نہیں گیا تھا...`,
}, {
    name: "RAG Story Generation",
    type: "story",
    description: "Generates Urdu stories by finding the best matching style using RAG technique.",
    prompt: "ایسی کہانی لکھیں جس میں ایک عورت اپنی برابری اور آزادی کی تلاش میں مختلف تجربات سے گزرتی ہے، اور آخر کار اسے اپنی اصل اہمیت کا احساس ہوتا ہے۔",
    output: `قصبہ ویران پڑا تھا...`,
}, {
    name: "Video Generation (Static)",
    type: "video",
    description: "Transforms Urdu stories into static scene videos with Urdu TTS voice-over.",
    videoSrc: "/static_output.mp4",
}, {
    name: "Video Generation (Fluid)",
    type: "video",
    description: "Creates animated Urdu videos with smooth scene motion and voice-over.",
    videoSrc: "/static_output.mp4",
}, {
    name: "History ChatBot",
    type: "chatbot",
    description: "An Urdu-based chatbot that answers historical and research questions with real-time web search.",
    prompt: "علامہ اقبال کے بارے میں بتائیں۔",
    output: `علامہ محمد اقبال برصغیر کے عظیم فلسفی تھے...`,
},];

export default function ExploreAsh() {
  const [activeIndex, setActiveIndex] = useState(null);

  return (
    <LayoutGroup>
      <div className="exploreAshPage">
        {/* ← header stays in normal flow at top */}
        <div className="headerWrapper"> {/* ← new */}
          <motion.h1
            initial={{ opacity: 0, y: -30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            Explore ASH AI Models
          </motion.h1>
        </div>

        {/* ← this wrapper will center its contents */}
        <div className="contentWrapper"> {/* ← new */}
          <div className="modelsContainer">
            {modelsInfo.map((model, i) => (
              <motion.div
                key={i}
                layout
                layoutId={`card-${i}`}
                className="modelCard"
                onClick={() => setActiveIndex(i)}
                whileHover={{ y: -5 }}
                transition={{ type: "spring", stiffness: 200, damping: 20 }}
              >
                <h2>{model.name}</h2>
                <p className="description">{model.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {activeIndex !== null && (
          <>
            <motion.div
              className="overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={() => setActiveIndex(null)}
            />

            <motion.div
              layoutId={`card-${activeIndex}`}
              className="modelCard expandedCard"
              onClick={(e) => e.stopPropagation()}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
            >
              <div className="expandedContent">
                <h2>{modelsInfo[activeIndex].name}</h2>
                <p className="description">{modelsInfo[activeIndex].description}</p>

                {modelsInfo[activeIndex].type === "video" ? (
                  <div className="videoContainer">
                    <video
                      src={modelsInfo[activeIndex].videoSrc}
                      muted
                      controls
                      playsInline
                      preload="auto"
                      autoPlay
                    />
                  </div>
                ) : (
                  <>
                    <p>
                      <strong>Prompt:</strong> {modelsInfo[activeIndex].prompt}
                    </p>
                    <div className="typingAnimation">
                      <TypeAnimation
                        sequence={[modelsInfo[activeIndex].output]}
                        wrapper="span"
                        cursor
                        speed={40}
                        omitDeletionAnimation
                      />
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </LayoutGroup>
  );
}
