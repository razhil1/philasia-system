import { Router } from "express";
import { db, items, categories, stock, movements, assetUnits } from "../db/index.js";
import { eq, desc, ilike, and, or, sql } from "drizzle-orm";
import multer from "multer";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const upload = multer({ dest: path.join(__dirname, "../../uploads/") });
const router = Router();

function requireAuth(req: any, res: any, next: any) {
  if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" });
  next();
}

router.get("/", requireAuth, async (req, res) => {
  try {
    const search = req.query.search as string || "";
    const type = req.query.type as string || "";
    let q = db.select({
      id: items.id, sku: items.sku, name: items.name, unit: items.unit,
      unitCost: items.unitCost, reorderLevel: items.reorderLevel,
      itemType: items.itemType, isActive: items.isActive, photo: items.photo,
      categoryId: items.categoryId, categoryName: categories.name,
    }).from(items).leftJoin(categories, eq(items.categoryId, categories.id));
    
    const conditions = [eq(items.isActive, true)];
    if (search) conditions.push(or(ilike(items.name, `%${search}%`), ilike(items.sku, `%${search}%`)) as any);
    if (type) conditions.push(eq(items.itemType, type));
    
    const rows = await q.where(and(...conditions)).orderBy(items.name);
    
    // Add stock quantities
    const enriched = await Promise.all(rows.map(async (item) => {
      let totalQty = 0;
      if (item.itemType === "asset") {
        const [ct] = await db.select({ count: sql<number>`count(*)` }).from(assetUnits)
          .where(and(eq(assetUnits.itemId, item.id), sql`status != 'scrapped'`));
        totalQty = Number(ct.count);
      } else {
        const [tot] = await db.select({ total: sql<string>`coalesce(sum(quantity),0)` }).from(stock).where(eq(stock.itemId, item.id));
        totalQty = parseFloat(tot.total);
      }
      const isLow = totalQty < parseFloat(item.reorderLevel || "0");
      return { ...item, totalQty, isLow };
    }));
    
    res.json(enriched);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.get("/:id", requireAuth, async (req, res) => {
  try {
    const [item] = await db.select({
      id: items.id, sku: items.sku, name: items.name, description: items.description,
      unit: items.unit, unitCost: items.unitCost, reorderLevel: items.reorderLevel,
      itemType: items.itemType, isActive: items.isActive, photo: items.photo,
      categoryId: items.categoryId, categoryName: categories.name, createdAt: items.createdAt,
    }).from(items).leftJoin(categories, eq(items.categoryId, categories.id))
      .where(eq(items.id, parseInt(req.params.id)));
    
    if (!item) return res.status(404).json({ error: "Item not found" });
    
    // Stock breakdown
    const stockRows = await db.select().from(stock).where(eq(stock.itemId, item.id));
    
    // Recent movements
    const recentMoves = await db.select().from(movements)
      .where(eq(movements.itemId, item.id))
      .orderBy(desc(movements.date)).limit(20);
    
    res.json({ ...item, stock: stockRows, recentMovements: recentMoves });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.post("/", requireAuth, upload.single("photo"), async (req, res) => {
  try {
    const { sku, name, description, categoryId, unit, unitCost, reorderLevel, itemType, isActive } = req.body;
    const [item] = await db.insert(items).values({
      sku, name, description: description || null,
      categoryId: categoryId ? parseInt(categoryId) : null,
      unit, unitCost: unitCost || "0", reorderLevel: reorderLevel || "0",
      itemType: itemType || "consumable",
      photo: req.file?.filename || null,
      isActive: isActive !== "false",
    }).returning();
    res.json(item);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.put("/:id", requireAuth, upload.single("photo"), async (req, res) => {
  try {
    const { sku, name, description, categoryId, unit, unitCost, reorderLevel, itemType, isActive } = req.body;
    const updateData: any = { sku, name, description: description || null, unit, unitCost: unitCost || "0",
      reorderLevel: reorderLevel || "0", itemType: itemType || "consumable",
      categoryId: categoryId ? parseInt(categoryId) : null, isActive: isActive !== "false" };
    if (req.file) updateData.photo = req.file.filename;
    const [item] = await db.update(items).set(updateData).where(eq(items.id, parseInt(req.params.id))).returning();
    res.json(item);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.delete("/:id", requireAuth, async (req, res) => {
  try {
    await db.update(items).set({ isActive: false }).where(eq(items.id, parseInt(req.params.id)));
    res.json({ ok: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
