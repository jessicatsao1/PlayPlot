import { Sparkles } from 'lucide-react';
import type { ComponentType } from 'react';

export type Item = {
  name: string;
  slug: string;
  disabled?: boolean;
  icon?: ComponentType<{ className?: string }>;
  description?: string;
};

export const demos: { name: string; items: Item[] }[] = [
  {
    name: 'Capabilities',
    items: [
      {
        name: 'Chatbox',
        icon: Sparkles,
        slug: 'chatbox',
        description: 'chatbox',
      },
    ],
  },
];

export function findDemoBySlug(slug: string): (Item & { category: string }) | undefined {
  for (const section of demos) {
    const item = section.items.find((item) => item.slug === slug);
    if (item) {
      return { ...item, category: section.name };
    }
  }
  return undefined;
}
