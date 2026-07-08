'use client'

import { motion } from 'motion/react'
import type { ReactNode } from 'react'

export function BlurFade({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return <motion.div
    initial={{ opacity: 0, filter: 'blur(8px)', y: 8 }}
    animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
    transition={{ duration: 0.45, delay, ease: 'easeOut' }}
    className={className}
  >{children}</motion.div>
}
