import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

export default [
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts", "public/**"] },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // Respons API sebagian besar belum diberi tipe. Utang lama ini ditandai sebagai
    // peringatan supaya terlihat, tanpa menghalangi lint kode baru yang lain.
    rules: { "@typescript-eslint/no-explicit-any": "warn" },
  },
];
