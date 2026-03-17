import express from "express";
import session from "express-session";
import connectPgSimple from "connect-pg-simple";
import passport from "passport";
import { Strategy as LocalStrategy } from "passport-local";
import bcrypt from "bcrypt";
import path from "path";
import { fileURLToPath } from "url";
import { db, users } from "./db/index.js";
import { eq } from "drizzle-orm";

// Routes
import authRouter from "./routes/auth.js";
import itemsRouter from "./routes/items.js";
import warehousesRouter from "./routes/warehouses.js";
import sitesRouter from "./routes/sites.js";
import movementsRouter from "./routes/movements.js";
import requestsRouter from "./routes/requests.js";
import reportsRouter from "./routes/reports.js";
import usersRouter from "./routes/users.js";
import categoriesRouter from "./routes/categories.js";
import dashboardRouter from "./routes/dashboard.js";
import assetUnitsRouter from "./routes/assetUnits.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = parseInt(process.env.PORT || "5000");

// Session store
const PgStore = connectPgSimple(session);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use("/uploads", express.static(path.join(__dirname, "../uploads")));

app.use(session({
  store: new PgStore({ conString: process.env.DATABASE_URL }),
  secret: process.env.SECRET_KEY || "philasia-pro-secret-2025",
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false, httpOnly: true, maxAge: 7 * 24 * 60 * 60 * 1000 },
}));

// Passport
passport.use(new LocalStrategy(async (username, password, done) => {
  try {
    const user = await db.select().from(users).where(eq(users.username, username)).limit(1);
    if (!user.length) return done(null, false, { message: "Invalid username or password." });
    const u = user[0];
    if (!u.isActive) return done(null, false, { message: "Account is deactivated." });
    const match = await bcrypt.compare(password, u.passwordHash || "");
    if (!match) return done(null, false, { message: "Invalid username or password." });
    // Update last login
    await db.update(users).set({ lastLogin: new Date() }).where(eq(users.id, u.id));
    return done(null, u);
  } catch (err) {
    return done(err);
  }
}));

passport.serializeUser((user: any, done) => done(null, user.id));
passport.deserializeUser(async (id: number, done) => {
  try {
    const user = await db.select().from(users).where(eq(users.id, id)).limit(1);
    done(null, user[0] || null);
  } catch (err) {
    done(err, null);
  }
});

app.use(passport.initialize());
app.use(passport.session());

// API Routes
app.use("/api/auth", authRouter);
app.use("/api/dashboard", dashboardRouter);
app.use("/api/items", itemsRouter);
app.use("/api/warehouses", warehousesRouter);
app.use("/api/sites", sitesRouter);
app.use("/api/movements", movementsRouter);
app.use("/api/requests", requestsRouter);
app.use("/api/reports", reportsRouter);
app.use("/api/users", usersRouter);
app.use("/api/categories", categoriesRouter);
app.use("/api/asset-units", assetUnitsRouter);

// Serve React app in production
const distPath = path.join(__dirname, "../dist/public");
app.use(express.static(distPath));
app.get("*", (_req, res) => {
  res.sendFile(path.join(distPath, "index.html"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`PhilAsia Pro running on http://0.0.0.0:${PORT}`);
});

export default app;
