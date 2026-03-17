import { Router } from "express";
import passport from "passport";
import bcrypt from "bcrypt";
import { db, users } from "../db/index.js";
import { eq } from "drizzle-orm";

const router = Router();

router.get("/me", (req, res) => {
  if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" });
  const u = req.user as any;
  res.json({ id: u.id, username: u.username, fullName: u.fullName, role: u.role, email: u.email });
});

router.post("/login", (req, res, next) => {
  passport.authenticate("local", (err: any, user: any, info: any) => {
    if (err) return next(err);
    if (!user) return res.status(401).json({ error: info?.message || "Login failed" });
    req.logIn(user, (err) => {
      if (err) return next(err);
      res.json({ id: user.id, username: user.username, fullName: user.fullName, role: user.role });
    });
  })(req, res, next);
});

router.post("/logout", (req, res) => {
  req.logout(() => res.json({ ok: true }));
});

router.post("/change-password", async (req, res) => {
  if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" });
  const u = req.user as any;
  const { currentPassword, newPassword } = req.body;
  const match = await bcrypt.compare(currentPassword, u.passwordHash || "");
  if (!match) return res.status(400).json({ error: "Current password is incorrect" });
  const hash = await bcrypt.hash(newPassword, 12);
  await db.update(users).set({ passwordHash: hash }).where(eq(users.id, u.id));
  res.json({ ok: true });
});

export default router;
