'use client'

import * as React from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger

export function DialogContent({ className, children, ...props }: React.ComponentProps<typeof DialogPrimitive.Content>) {
  return <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/20 backdrop-blur-[2px] data-[state=open]:animate-in" />
    <DialogPrimitive.Content className={cn('fixed bottom-4 right-4 z-50 flex max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-2xl outline-none', className)} {...props}>
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 text-neutral-400 hover:text-neutral-950"><X className="h-4 w-4" /><span className="sr-only">Close</span></DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>
}

export const DialogTitle = DialogPrimitive.Title
export const DialogDescription = DialogPrimitive.Description
