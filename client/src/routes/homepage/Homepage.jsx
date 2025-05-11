import { Link } from "react-router-dom";
import "./homepage.css";
import { TypeAnimation } from "react-type-animation";
import { useState } from "react";

const Homepage = () => {
  const [typingStatus, setTypingStatus] = useState("human1");

  return (
    <div className="homepage">
      <img src="/orbital.png" alt="" className="orbital" />
      <div className="left">
        <h1>ASH AI</h1>
        <h2>Urdu Story Generation</h2>
        <h3>اپنی تخلیقی صلاحیتوں کو آزاد کریں</h3>

        {/* Buttons container */}
        <div className="buttons">
          <Link to="/dashboard" className="startButton">شروع کریں</Link>
          <Link to="/explore-ash" className="exploreButton">Explore ASH AI</Link>
        </div>

      </div>
      <div className="right">
        <div className="imgContainer">
          <div className="bgContainer">
            <div className="bg"></div>
          </div>
          <img src="/bot.png" alt="" className="bot" />
          <div className="chat">
            <img
              src={
                typingStatus === "human1"
                  ? "/human1.jpeg"
                  : typingStatus === "human2"
                  ? "/human2.jpeg"
                  : "bot.png"
              }
              alt=""
            />
            <TypeAnimation
              sequence={[
                'Human:جنگجوؤں کے بارے میں ایک کہانی لکھیں',
                2000, () => { setTypingStatus("bot") },
                'Bot:ایک زمانے میں، ایک بادشاہ تھا جس کا نام سکندر تھا۔ وہ ایک بہت ہی طاقتور بادشاہ تھا اور اس نے بہت سے علاقے فتح کیے تھے۔ ایک دن، سکندر نے ایران پر حملہ کرنے کا فیصلہ کیا۔ ایران کا بادشاہ دارا تھا۔ وہ بھی ایک بہت ہی طاقتور بادشاہ تھا اور اس نے اپنی سلطنت کی حفاظت کے لیے ایک بڑی فوج جمع کی تھی۔....',
                2000, () => { setTypingStatus("human2") },
                'Human2:کھیت میں خوشحال جانوروں کے بارے میں ایک کہانی لکھیں',
                2000, () => { setTypingStatus("bot") },
                'Bot:ایک بار ایک کھیت تھا جہاں بہت سے جانور رہتے تھے۔ وہاں گھوڑے، گائے، بھیڑیں، بکریاں اور مرغیاں تھیں۔ وہ سب ایک ساتھ مل کر رہتے تھے اور بہت خوش تھے۔........',
                2000, () => { setTypingStatus("human1") },
              ]}
              wrapper="span"
              repeat={Infinity}
              cursor={true}
              omitDeletionAnimation={true}
            />
          </div>
        </div>
      </div>

      <div className="terms">
        <img src="/logo.png" alt="" />
        <div className="links">
          <Link to="/">Terms of Service</Link>
          <span>|</span>
          <Link to="/">Privacy Policy</Link>
        </div>
      </div>
    </div>
  );
};

export default Homepage;
