'use client'

import { useMemo } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { useVoice } from '@/context/voice-context'
import {
  buildNavCommands,
  buildVoiceCommands,
  buildContentCommands,
  buildCommentCommands,
  COMMAND_CATEGORIES,
  type VoiceCommand,
} from '@/lib/voice-commands'

interface CommandGroup {
  category: string
  label: string
  icon: string
  commands: VoiceCommand[]
}

export function VoiceHelpPanel() {
  const { showHelp, setShowHelp, lastCommand, startListening, stopListening } = useVoice()

  const groups: CommandGroup[] = useMemo(() => {
    const noop = () => {}
    const push = (_path: string) => {}

    return [
      {
        ...COMMAND_CATEGORIES[0],
        commands: buildVoiceCommands(startListening, stopListening, () => setShowHelp(true)),
      },
      {
        ...COMMAND_CATEGORIES[1],
        commands: buildNavCommands(push),
      },
      {
        ...COMMAND_CATEGORIES[2],
        commands: buildContentCommands(noop, noop, noop, noop),
      },
      {
        ...COMMAND_CATEGORIES[3],
        commands: buildCommentCommands(noop, noop, noop, noop),
      },
    ]
  }, [startListening, stopListening, setShowHelp])

  return (
    <Dialog open={showHelp} onOpenChange={setShowHelp}>
      <DialogContent className="max-h-[80vh] overflow-y-auto">
        <DialogTitle className="text-base font-semibold">
          🎤 语音命令参考
        </DialogTitle>
        <p className="text-xs text-neutral-400 mt-1 mb-4">
          说出命令即可控制页面，无需打字
        </p>

        <div className="space-y-4">
          {groups.map((group) => (
            <div key={group.category}>
              <h3 className="text-xs font-semibold text-neutral-500 mb-2 flex items-center gap-1.5">
                <span>{group.icon}</span>
                <span>{group.label}</span>
              </h3>
              <div className="grid gap-1.5">
                <AnimatePresence mode="popLayout">
                  {group.commands.map((cmd) => {
                    const isActive = lastCommand?.id === cmd.id
                    return (
                      <motion.div
                        key={cmd.id}
                        layout
                        animate={
                          isActive
                            ? {
                                backgroundColor: 'rgb(239 246 255)',
                                borderColor: 'rgb(147 197 253)',
                              }
                            : {
                                backgroundColor: 'rgb(255 255 255)',
                                borderColor: 'rgb(229 229 229)',
                              }
                        }
                        transition={{ duration: 0.3 }}
                        className="flex items-center gap-2 rounded-lg border px-3 py-2"
                      >
                        <span className="text-xs font-medium text-neutral-700 shrink-0">
                          {cmd.keywords[0]}
                        </span>
                        {cmd.keywords.length > 1 && (
                          <span className="text-[10px] text-neutral-400">
                            {cmd.keywords.slice(1).join(' / ')}
                          </span>
                        )}
                        <span className="flex-1" />
                        <span className="text-[10px] text-neutral-400">
                          {cmd.description}
                        </span>
                      </motion.div>
                    )
                  })}
                </AnimatePresence>
              </div>
            </div>
          ))}
        </div>

        <p className="text-[10px] text-neutral-400 mt-4 pt-3 border-t border-neutral-100">
          提示：说「帮助」随时打开此面板，说「关闭语音」停止语音控制
        </p>
      </DialogContent>
    </Dialog>
  )
}
