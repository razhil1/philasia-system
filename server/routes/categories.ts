import { Router } from "express";
import { db, categories, items } from "../db/index.js";
import { eq, sql } from "drizzle-orm";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };

router.get("/", auth, async (_req, res) => {
  try {
    const rows = await db.select().from(categories).orderBy(categories.name);
    const enriched = await Promise.all(rows.map(async (cat) => {
      const [ct] = await db.select({ count: sql<number>`count(*)` }).from(items).where(eq(items.categoryId, cat.id));
      return { ...cat, itemCount: Number(ct.count) };
    }));
    res.json(enriched);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/", auth, async (req, res) => {
  try {
    const { name, description } = req.body;
    const [row] = await db.insert(categories).values({ name, description }).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.put("/:id", auth, async (req, res) => {
  try {
    const { name, description } = req.body;
    const [row] = await db.update(categories).set({ name, description }).where(eq(categories.id, parseInt(req.params.id))).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.delete("/:id", auth, async (req, res) => {
  try {
    await db.delete(categories).where(eq(categories.id, parseInt(req.params.id)));
    res.json({ ok: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
