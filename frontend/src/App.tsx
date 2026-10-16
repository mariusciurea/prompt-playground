import { Navigate, Route, Routes } from "react-router-dom";

import { RequireAccess, RequireAuth, RequireStaff } from "@/components/guards";
import { Shell } from "@/components/Shell";
import { AdminPage } from "@/pages/Admin";
import { Dashboard } from "@/pages/Dashboard";
import { Engage } from "@/pages/Engage";
import { ForgotPassword, ResetPassword } from "@/pages/ForgotPassword";
import { Learn } from "@/pages/Learn";
import { Login } from "@/pages/Login";
import { Playground } from "@/pages/Playground";
import { Register } from "@/pages/Register";
import { Reservation } from "@/pages/Reservation";
import { SkillsLab } from "@/pages/SkillsLab";
import { VerifyEmail } from "@/pages/VerifyEmail";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="learn" element={<Learn />} />
        <Route
          path="playground"
          element={
            <RequireAccess>
              <Playground />
            </RequireAccess>
          }
        />
        <Route
          path="engage"
          element={
            <RequireAccess>
              <Engage />
            </RequireAccess>
          }
        />
        <Route
          path="reservation"
          element={
            <RequireAccess>
              <Reservation />
            </RequireAccess>
          }
        />
        <Route
          path="skills-lab"
          element={
            <RequireAccess>
              <SkillsLab />
            </RequireAccess>
          }
        />
        <Route
          path="admin/*"
          element={
            <RequireStaff>
              <AdminPage />
            </RequireStaff>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
