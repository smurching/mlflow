package org.mlflow.spark.autologging


import scala.reflect.runtime.{universe => ru}
import java.lang.reflect.Method

import org.slf4j.LoggerFactory

object ReflectionUtils {
  private val logger = LoggerFactory.getLogger(getClass)
  private val rm = ru.runtimeMirror(getClass.getClassLoader)

  /** Get Scala object by its fully-qualified name */
  def getScalaObjectByName(name: String): Any = {
    val module = rm.staticModule(name)
    val obj = rm.reflectModule(module)
    obj.instance
  }

  def isInstanceOf(obj: Any, className: String): Boolean = {
    val clazz = getClass.getClassLoader.loadClass(className)
    clazz.isInstance(obj)
//    val classOpt = try {
//        Option(rm.staticClass(className))
//    } catch {
//      case e: scala.ScalaReflectionException =>
////        logger.info(s"Exception while checking if object $obj is of type $className. " +
////          s"Exception:\n${ExceptionUtils.serializeException(e)}")
//        None
//    }
//    // If class is loadable, check whether object has same type, otherwise return false
//    classOpt.exists { c =>
//      val desiredType = c.toType
//      val objectTypeTag = ru.typeTag[T]
//      println(s"Desired type ${desiredType}, actual type ${objectTypeTag.tpe}, object classname ${obj.getClass.getCanonicalName}")
//      objectTypeTag.tpe <:< desiredType
//    }
  }


  def getField(obj: Any, fieldName: String): Any = {
//    val instanceMirror = rm.reflect(obj)
//    val objTypeTag = ru.typeTag[T]
//    val desiredField = objTypeTag.tpe.decl(ru.TermName(fieldName)).asTerm
//    val field = instanceMirror.reflectField(desiredField)
//    field.get.asInstanceOf[T]
    val declaredFields = obj.getClass.getDeclaredFields
    val field = declaredFields.find(_.getName == fieldName).getOrElse {
      throw new RuntimeException(s"Unable to get field '$fieldName' in object with class " +
        s"${obj.getClass.getName}. Available fields: " +
        s"[${declaredFields.map(_.getName).mkString(", ")}]")
    }
    field.setAccessible(true)
    field.get(obj)
  }

  /**
    * Call method with provided name on the specified object. The method name is assumed to be
    * unique
    */
  def callMethod(obj: Any, name: Any, args: Seq[Object]): Any = {
    val declaredMethods = obj.getClass.getDeclaredMethods
    val method = declaredMethods.find(_.getName == name).getOrElse(
      throw new RuntimeException(s"Unable to find method with name $name of object with class " +
        s"${obj.getClass.getName}. Available methods: " +
        s"[${declaredMethods.map(_.getName).mkString(", ")}]"))
    method.invoke(obj, args: _*)
  }
}
