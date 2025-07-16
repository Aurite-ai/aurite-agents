import * as React from "react"
import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, onCheckedChange, checked, disabled, ...props }, ref) => {
    const [internalChecked, setInternalChecked] = React.useState(checked || false)
    
    // Sync internal state with external checked prop
    React.useEffect(() => {
      setInternalChecked(checked || false)
    }, [checked])

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newChecked = e.target.checked
      setInternalChecked(newChecked)
      onCheckedChange?.(newChecked)
    }

    return (
      <div className="relative inline-flex items-center">
        <input
          type="checkbox"
          className="sr-only"
          ref={ref}
          checked={internalChecked}
          onChange={handleChange}
          disabled={disabled}
          {...props}
        />
        <div
          className={cn(
            "h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background transition-all duration-200 flex items-center justify-center cursor-pointer",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            internalChecked 
              ? "bg-primary border-primary text-primary-foreground" 
              : "border-input bg-background hover:bg-accent",
            disabled && "cursor-not-allowed opacity-50",
            className
          )}
          onClick={() => {
            if (!disabled) {
              const newChecked = !internalChecked
              setInternalChecked(newChecked)
              onCheckedChange?.(newChecked)
            }
          }}
        >
          {internalChecked && (
            <Check className="h-3 w-3 text-current" strokeWidth={3} />
          )}
        </div>
      </div>
    )
  }
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
