import { Router } from "express";
import { db, users } from "../db/index.js";
import { eq } from "drizzle-orm";
import bcrypt from "bcrypt";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };
const admin = (req: any, res: any, next: any) => { if ((req.user as any)?.role !== "admin") return res.status(403).json({ error: "Forbidden" }); next(); };

router.get("/", auth, admin, async (_req, res) => {
  try {
    const rows = await db.select({ id: users.id, username: users.username, email: users.email, fullName: users.fullName, role: users.role, isActive: users.isActive, createdAt: users.createdAt, lastLogin: users.lastLogin }).from(users).orderBy(users.fullName);
    res.json(rows);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/", auth, admin, async (req, res) => {
  try {
    const { username, email, fullName, role, password, isActive } = req.body;
    const hash = await bcrypt.hash(password, 12);
    const [row] = await db.insert(users).values({ username, email, fullName, role, passwordHash: hash, isActive: isActive !== false }).returning({ id: users.id, username: users.username, email: users.email, fullName: users.fullName, role: users.role, isActive: users.isActive });
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.put("/:id", auth, admin, async (req, res) => {
  try {
    const { email, fullName, role, isActive, password } = req.body;
    const update: any = { email, fullName, role, isActive };
    if (password) update.passwordHash = await bcrypt.hash(password, 12);
    const [row] = await db.update(users).set(update).where(eq(users.id, parseInt(req.params.id))).returning({ id: users.id, username: users.username, email: users.email, fullName: users.fullName, role: users.role, isActive: users.isActive });
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.patch("/:id/toggle", auth, admin, async (req, res) => {
  try {
    const [user] = await db.select().from(users).where(eq(users.id, parseInt(req.params.id)));
    const [row] = await db.update(users).set({ isActive: !user.isActive }).where(eq(users.id, user.id)).returning({ id: users.id, isActive: users.isActive });
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
