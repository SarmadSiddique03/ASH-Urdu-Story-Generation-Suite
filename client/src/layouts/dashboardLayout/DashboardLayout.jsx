import { Outlet, useNavigate } from "react-router-dom";
import "./dashboardLayout.css";
import { useAuth } from "@clerk/clerk-react";
import { useEffect, useState } from "react";
import ChatList from "../../components/chatList/ChatList";

const DashboardLayout = () => {
  const { userId, isLoaded } = useAuth();
  const navigate = useNavigate();

  // 🟢 Move state here so it can be passed down
  const [selectedType, setSelectedType] = useState("Story Generation");

  useEffect(() => {
    if (isLoaded && !userId) {
      navigate("/sign-in");
    }
  }, [isLoaded, userId, navigate]);

  if (!isLoaded) return "Loading...";

  return (
    <div className="dashboardLayout">
      <div className="menu">
        <ChatList selectedType={selectedType} />
      </div>
      <div className="content">
        <Outlet context={{ selectedType, setSelectedType }} />
      </div>
    </div>
  );
};

export default DashboardLayout;
